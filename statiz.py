import re
from bs4 import BeautifulSoup
from selenium import webdriver
import pandas as pd
import utils
import requests


class StatizCrawler:
    # WEBDRIVER_PATH = 'D:/IT/mywork/chromedriver.exe'
    # XPATH = '//*[@id="mytable"]/tbody'

    OPTIONS = webdriver.ChromeOptions()
    OPTIONS.add_argument('--headless')
    OPTIONS.add_argument('--no-sandbox')
    OPTIONS.add_argument('--disable-dev-shm-usage')
    OPTIONS.add_argument('disable-gpu')

    U = 'http://www.statiz.co.kr/stat.php?opt=0&sopt=0&re=0&ys='
    R = '&ye='
    L = '&se=0&te=&tm=&ty=0&qu=auto&po=0&as=&ae=&hi=&un=&pl=&da=1&o1=WAR_ALL_ADJ' \
        '&de=1&lr=0&tr=&cv=&ml=1&sn=1000&si=&cn=500'

    def __init__(self, driver_path):
        """
        Creates new instance of the Statiz website crawler. (http://www.statiz.co.kr)

            :param driver_path: Chrome driver path
        """

        self.birth_regex = re.compile(r'\d{4}-\d{2}-\d{2}')
        self.name_regex = re.compile(r'\d+(.*\d{2})?')
        self.position_regex = re.compile(r'(1B|2B|3B|SS|C|LF|RF|CF|DH|P)$')

        self.driver = webdriver.Chrome(driver_path, options=self.OPTIONS)
        # self.record_df = pd.DataFrame(columns=['name', 'season', 'birth', 'team', 'position'])

        # self.url = self.U + str(year) + self.R + str(year) + self.L

    def crawl_records(self, year=1982):
        """
        Crawl KBO Batter records of the given year.
        If 'year' parameter were not given, it would crawl the 1982's record. (KBO launch year)

            :param year: (int) A year to crawl
            :return: (DataFrame) A DataFrame with crawled records
        """

        url = 'http://www.statiz.co.kr/stat.php?opt=0&sopt=0&re=0&ys={0}&ye={0}&se=0&te=&tm=&ty=0&qu=auto&po=' \
              '0&as=&ae=&hi=&un=&pl=&da=1&o1=WAR_ALL_ADJ&de=1&lr=0&tr=&cv=&ml=1&sn=1000&si=&cn=500'.format(year)
        url = self.U + str(year) + self.R + str(year) + self.L
        xpath = '//*[@id="mytable"]/tbody'
        record_df = pd.DataFrame(columns=['name', 'season', 'birth', 'team', 'position'])

        # driver = webdriver.Chrome(self.WEBDRIVER_PATH, options=self.OPTIONS)
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

            tmp = tr
            tr = pd.Series(tr.text.strip().replace('\n', '').split(' '))

            if len(tr) == 1:
                continue

            birth = ''.join(self.birth_regex.findall(tmp.find('a')['href']))
            name = ''.join(self.name_regex.findall(tr[0]))
            position = ''.join(self.position_regex.findall(tr[0]))

            team_regex = re.compile(name + '(.*)?' + position)
            team = ''.join(team_regex.findall(tr[0]))

            tr = tr.replace('', pd.NA)
            tr['name'] = name[:-2]
            tr['season'] = name[-2:]
            tr['birth'] = birth
            tr['team'] = team
            tr['position'] = position

            record_df = record_df.append(tr, ignore_index=True)

        self.driver.close()

        return record_df.dropna(axis=1)

    def crawl_rename(self):
        """
        Crawl the player list that change their name.

            :return: (DataFrame) A DataFrame with renamed player list
        """

        rename_df = pd.DataFrame()
        url = 'http://www.statiz.co.kr/rename.php'
        # regex = re.compile(r'\d{4}-\d{2}-\d{2}')

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


# remove?
def set_columns(df):
    """
    Rename column names and remove unnecessary columns.
        :param df: A DataFrame
        :return: A DataFrame that columns changed
    """

    df = df.dropna(axis=1).drop([0, 53], axis=1)
    df.columns = ['Name', 'Season', 'Birth', 'Team', 'Position', 'WAR', 'G', 'PA', 'AB', 'R', 'H', '2B',
                  '3B', 'HR', 'TB', 'RBI', 'SB', 'CB', 'BB', 'HBP', 'IBB', 'SO', 'DP', 'SH', 'SF']

    return df


if __name__ == '__main__':
    FILE_PATH1 = r'D:\IT\mywork\Project\KBO-Analysis\dataset\kbo_batter.xlsx'
    FILE_PATH2 = r'D:\IT\mywork\Project\KBO-Analysis\dataset\rename.xlsx'
    DRIVER_PATH = r'D:\IT\mywork\chromedriver.exe'

    records = pd.DataFrame()

    sc = StatizCrawler(DRIVER_PATH)
    for year in range(1982, 2021):
        records = records.append(sc.crawl_records(year), ignore_index=True)

    # baseball = set_columns(baseball)
    records = records.dropna(axis=1).drop([0, 53], axis=1)
    records.columns = ['Name', 'Season', 'Birth', 'Team', 'Position', 'WAR', 'G', 'PA', 'AB', 'R', 'H', '2B',
                       '3B', 'HR', 'TB', 'RBI', 'SB', 'CB', 'BB', 'HBP', 'IBB', 'SO', 'DP', 'SH', 'SF']

    rename = sc.crawl_rename()
    print(records.head())
    print(records.tail())
    print(rename)

    records.to_excel(FILE_PATH1, encoding='utf-8', index=False)
    rename.to_excel(FILE_PATH2, encoding='utf-8', index=False)
