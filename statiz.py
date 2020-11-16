import re
from bs4 import BeautifulSoup
from selenium import webdriver
import pandas as pd
import utils
import requests


class StatizCrawler:
    """
        A class to crawl Statiz website. (http://www.statiz.co.kr)

            Parameter
                driver_path : (str) Chrome driver path

            Methods
                crawl_records(year=) : Return crawled KBO Batter records

                crawl_rename( ) : Return crawled rename player list

    """

    OPTIONS = webdriver.ChromeOptions()
    OPTIONS.add_argument('--headless')
    OPTIONS.add_argument('--no-sandbox')
    OPTIONS.add_argument('--disable-dev-shm-usage')
    OPTIONS.add_argument('disable-gpu')

    def __init__(self, driver_path):
        self.birth_regex = re.compile(r'\d{4}-\d{2}-\d{2}')
        self.name_regex = re.compile(r'\d+(.*\d{2})?')
        self.position_regex = re.compile(r'(1B|2B|3B|SS|C|LF|RF|CF|DH|P)$')

        self.driver = webdriver.Chrome(driver_path, options=self.OPTIONS)

    def __del__(self):
        self.driver.quit()

    def crawl_records(self, year=1982):
        """
            Crawl KBO Batter records of the given year.
            If 'year' parameter were not given, it would crawl the 1982's record. (KBO launch year)

                :param year: (int) A year to crawl
                :return: (DataFrame) A DataFrame with crawled records
        """

        record_df = pd.DataFrame(columns=['name', 'season', 'birth', 'team', 'position'])
        url = 'http://www.statiz.co.kr/stat.php?opt=0&sopt=0&re=0&ys={0}&ye={0}&se=0&te=&tm=&ty=0&qu=auto&po=' \
              '0&as=&ae=&hi=&un=&pl=&da=1&o1=WAR_ALL_ADJ&de=1&lr=0&tr=&cv=&ml=1&sn=1000&si=&cn=500'.format(year)
        xpath = '//*[@id="mytable"]/tbody'

        self.driver.get(url)
        self.driver.implicitly_wait(5)

        html = self.driver.find_element_by_xpath(xpath).get_attribute("innerHTML")
        page = BeautifulSoup(html, 'lxml')
        trs = page.findAll('tr')

        count = 1
        print('Now Crawling : {}'.format(year))

        for tr in trs:
            utils.progress_bar(count, len(trs))
            count += 1

            birth = ''.join(self.birth_regex.findall(tr.find('a')['href']))
            tr = tr.text.strip().replace('\n', '')

            if tr[:3] in ['순이름', 'WAR']:
                continue

            tr = pd.Series(tr.split(' ')).replace('', pd.NA)

            name = ''.join(self.name_regex.findall(tr[0]))
            position = ''.join(self.position_regex.findall(tr[0]))

            team_regex = re.compile(name + '(.*)?' + position)
            team = ''.join(team_regex.findall(tr[0]))

            for i in list(range(1, 54, 2)):
                if tr[i] is pd.NA:
                    tr[i] = 0

            tr['name'] = name[:-2]
            tr['season'] = name[-2:]
            tr['birth'] = birth
            tr['team'] = team
            tr['position'] = position

            record_df = record_df.append(tr, ignore_index=True)

        if year < 2014:
            record_df = record_df.dropna(axis=1).drop([0, 53], axis=1)
        else:
            record_df = record_df.dropna(axis=1).drop([0, 53, 55], axis=1)  # Statiz record includes WPA after 2014

        record_df.columns = ['Name', 'Season', 'Birth', 'Team', 'Position', 'WAR', 'G', 'PA', 'AB', 'R', 'H', '2B',
                             '3B', 'HR', 'TB', 'RBI', 'SB', 'CB', 'BB', 'HBP', 'IBB', 'SO', 'DP', 'SH', 'SF', 'AVG',
                             'OBP', 'SLG', 'OPS', 'wOBA', 'WRC+']
        return record_df

    def crawl_rename(self):
        """
            Crawl the player list that change their name.

                :return: (DataFrame) A DataFrame with renamed player list
        """

        rename_df = pd.DataFrame()
        url = 'http://www.statiz.co.kr/rename.php'

        html = requests.get(url)
        page = BeautifulSoup(html.text, 'lxml')
        trs = page.findAll('tr')

        count = 1
        print('Now Crawling : Renamed Player')

        for tr in trs:
            utils.progress_bar(count, len(trs))
            count += 1
            tmp = []

            tds = tr.findAll('td')

            if len(tds) == 1:
                continue

            for td in tds:
                tmp.append(td.text)

                if td.find('a'):
                    birth = ''.join(self.birth_regex.findall(td.find('a')['href']))
                    tmp.append(birth)

            rename_df = rename_df.append(pd.Series(tmp), ignore_index=True)

        rename_df.columns = ['Year', 'Before', 'After', 'Birth', 'Team']
        rename_df.drop(0, inplace=True)
        rename_df.reset_index(drop=True, inplace=True)

        for idx in rename_df.index:
            team = rename_df.loc[idx, 'Team']
            if team == 'KIA':
                team = '기아'

            rename_df.loc[idx, 'Team'] = team[:1]

        return rename_df


if __name__ == '__main__':
    FILE_PATH1 = r'D:\IT\mywork\Project\KBO-Analysis\dataset\kbo_batter.xlsx'
    FILE_PATH2 = r'D:\IT\mywork\Project\KBO-Analysis\dataset\rename.xlsx'
    DRIVER_PATH = r'D:\IT\mywork\chromedriver.exe'

    records = pd.DataFrame()
    sc = StatizCrawler(DRIVER_PATH)

    for year in range(1982, 2021):
        records = records.append(sc.crawl_records(year), ignore_index=True)

    rename = sc.crawl_rename()

    print(records.head())
    print(records.tail())
    print(rename)

    del sc

    records.to_excel(FILE_PATH1, encoding='utf-8', index=False)
    rename.to_excel(FILE_PATH2, encoding='utf-8', index=False)
