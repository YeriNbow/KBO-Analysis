import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import Select
import time
import pandas as pd
import requests
import utils


class PosException(Exception):
    def __str__(self):
        return "Wrong 'pos' parameter was given. Choose 'B' to crawl batter records, or 'P' to crawl pitcher records."


class StatizCrawler:
    """
        A class to crawl Statiz website. (http://www.statiz.co.kr)

            Parameter
                driver_path : (str) Chrome driver path.

            Methods
                crawl_player(year=, pos=) : Returns a DataFrame of player records.

                crawl_team(year=) : Returns a DataFrame of team records.

                crawl_team_rank(year=) : Returns a DataFrame of team rank.

                crawl_rename( ) : Returns a DataFrame of renamed players.
    """

    def __init__(self, driver_path):
        # regex
        self.birth_regex = re.compile(r'\d{4}-\d{2}-\d{2}')
        self.name_regex = re.compile(r'\d+(.*\d{2})?')
        self.position_regex = re.compile(r'(1B|2B|3B|SS|C|LF|RF|CF|DH|P)$')

        # driver settings
        self.OPTIONS = webdriver.ChromeOptions()
        self.OPTIONS.add_argument('--headless')
        self.OPTIONS.add_argument('--no-sandbox')
        self.OPTIONS.add_argument('--disable-dev-shm-usage')
        self.OPTIONS.add_argument('disable-gpu')

        self.driver = webdriver.Chrome(driver_path, options=self.OPTIONS)

        # columns to drop
        self.drop_always = [i for i in range(0, 54, 2)]

        # KT와 KIA의 팀 약어가 겹침(K)
        self.kt_player = self.__check_kt()

    def __check_kt(self):
        url = 'http://www.statiz.co.kr/stat.php?mid=stat&re=0&ys=1982&ye=2020&se=0&te=kt&tm=&ty=0&qu=auto' \
              '&po=0&as=&ae=&hi=&un=&pl=&da=1&o1=WAR_ALL_ADJ&o2=TPA&de=1&lr=0&tr=&cv=&ml=1&pa=0&si=&cn=Year' \
              '%2C%2C0%2CRBI%2C%2C5000&sn=500'

        response = requests.get(url)
        page = BeautifulSoup(response.text, 'lxml')
        trs = page.findAll('tr')
        kt = []

        for tr in trs:
            tr = tr.text.strip().replace('\n', '')
            tr = pd.Series(tr.split(' '))

            if len(tr) < 50:
                continue

            name = ''.join(self.name_regex.findall(tr[0]))

            if name:
                kt.append(name[:-2])

        return kt

    def __del__(self):
        self.driver.quit()

    def crawl_player(self, year=1982, pos='B'):
        """
            Crawl KBO player records of the given year and position.
            If parameters were not given, it would crawl the 1982's 'Batter' records.

                :param int year: A year to crawl. Default is 1982. (KBO launch year)
                :param str pos: Position to crawl. Default is 'B'. ('B' for Batter / 'P' for Pitcher)
                :return: (DataFrame) A DataFrame with crawled records.
                :raise PosException: If 'pos' is not 'B' or 'P'.
        """

        try:
            if pos == 'B':
                url = 'http://www.statiz.co.kr/stat.php?opt=0&sopt=0&re=0&ys={0}&ye={0}&se=0&te=&tm=&ty=0' \
                      '&qu=auto&po=0&as=&ae=&hi=&un=&pl=&da=1&o1=WAR_ALL_ADJ&de=1&lr=0&tr=&cv=&' \
                      'ml=1&sn=1000&si=&cn=500'.format(year)

                record_df = pd.DataFrame(columns=['Name', 'Season', 'Birth', 'Team', 'Position', 'WAR', 'G',
                                                  'PA', 'AB', 'R', 'H', '2B', '3B', 'HR', 'TB', 'RBI', 'SB',
                                                  'CB', 'BB', 'HBP', 'IBB', 'SO', 'DP', 'SH', 'SF', 'AVG',
                                                  'OBP', 'SLG', 'OPS', 'wOBA', 'WRC+'])

            elif pos == 'P':
                url = 'http://www.statiz.co.kr/stat.php?opt=0&sopt=0&re=1&ys={0}&ye={0}&se=0&te=&tm=&ty=0&qu=' \
                      'auto&po=0&as=&ae=&hi=&un=&pl=&da=1&o1=WAR&o2=OutCount&de=1' \
                      '&lr=0&tr=&cv=&ml=1&sn=300&si=&cn=500'.format(year)

                record_df = pd.DataFrame(columns=['Name', 'Season', 'Birth', 'Team', 'WAR', 'G', 'CG', 'SHO', 'GS',
                                                  'W', 'L', 'SV', 'HLD', 'IP', 'R', 'ER', 'TBF', 'H', 'HR', 'BB',
                                                  'IBB', 'HBP', 'K', 'WP', 'VK', 'ERA', 'FIP', 'WHIP', 'ERA+', 'FIP+'])
            else:
                raise PosException

        except PosException as pe:
            print(pe)
            return

        xpath = '//*[@id="mytable"]/tbody'

        self.driver.get(url)
        self.driver.implicitly_wait(5)

        html = self.driver.find_element_by_xpath(xpath).get_attribute("innerHTML")
        page = BeautifulSoup(html, 'lxml')
        trs = page.findAll('tr')

        count = 1
        print('Now Crawling : {0} {1} records'.format(year, 'Batter' if pos == 'B' else 'Pitcher'))

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

            tr['name'] = name[:-2]
            tr['season'] = name[-2:]
            tr['birth'] = birth

            if tr['name'] in self.kt_player and 'K' in team:
                team = team.replace('K', '케')
                tr['team'] = team
            else:
                tr['team'] = team

            if pos == 'B':
                tr['position'] = position

                # Statiz does not support batter's WPA records before 2014.
                if year < 2014:
                    tr.drop(self.drop_always + [53], inplace=True)  # 53: duplicated column (WAR)
                else:
                    tr.drop(self.drop_always + [53, 54, 55], inplace=True)

                tr.index = ['WAR', 'G', 'PA', 'AB', 'R', 'H', '2B', '3B', 'HR', 'TB', 'RBI', 'SB', 'CB', 'BB',
                            'HBP', 'IBB', 'SO', 'DP', 'SH', 'SF', 'AVG', 'OBP', 'SLG', 'OPS', 'wOBA', 'WRC+',
                            'Name', 'Season', 'Birth', 'Team', 'Position']

            else:
                # Statiz does not support pitcher's WPA, 2B, 3B records before 2014.
                if year < 2014:
                    tr.drop(self.drop_always + [53], inplace=True)  # 53: duplicated column (WAR)
                else:
                    tr.drop(self.drop_always + [29, 31, 54, 56, 57, 58, 59], inplace=True)

                tr.index = ['WAR', 'G', 'CG', 'SHO', 'GS', 'W', 'L', 'SV', 'HLD', 'IP', 'R', 'ER', 'TBF', 'H',
                            'HR', 'BB', 'IBB', 'HBP', 'K', 'WP', 'VK', 'ERA', 'FIP', 'WHIP', 'ERA+', 'FIP+',
                            'Name', 'Season', 'Birth', 'Team']

            record_df = record_df.append(tr, ignore_index=True)

        return record_df

    def crawl_team(self, year=1982):
        """
            Crawl KBO team records of the given year.

            :param int year: A year to crawl. Default is 1982. (KBO launch year)
            :return: (DataFrame) A DataFrame with crawled records.
        """

        team_df = pd.DataFrame(columns=['Team', 'Season'])
        url = 'http://www.statiz.co.kr/stat.php?opt=0&sopt=0&re=0&ys={0}&ye={0}&se=0&te=&tm=&ty=0' \
              '&qu=auto&po=0&as=&ae=&hi=&un=&pl=&da=1&o1=WAR_ALL_ADJ&o2=TPA&de=1&' \
              'lr=5&tr=&cv=&ml=1&sn=30&si=&cn='.format(year)

        html = requests.get(url)
        page = BeautifulSoup(html.text, 'lxml')
        trs = page.findAll('tr')

        count = 1
        print('Now Crawling : {0} team records'.format(year))

        for tr in trs:
            utils.progress_bar(count, len(trs))
            count += 1

            tr = tr.text.strip().replace('\n', '')
            tr = pd.Series(tr.split(' '))

            if len(tr) < 50:
                continue

            name = ''.join(self.name_regex.findall(tr[0]))
            tr['Team'] = name[:-2]
            tr['Season'] = name[-2:]
            team_df = team_df.append(tr, ignore_index=True)

        team_df.dropna(inplace=True)
        team_df.reset_index(drop=True, inplace=True)

        if year < 2014:
            # Statiz does not support WPA before 2014.
            team_df.drop(self.drop_always + [53], axis=1, inplace=True)
        else:
            team_df.drop(self.drop_always + [53, 54, 55], axis=1, inplace=True)  # remove duplicates.

        team_df.drop([0], axis=0, inplace=True)

        team_df.columns = ['Team', 'Season', 'WAR', 'G', 'PA', 'AB', 'R', 'H', '2B', '3B', 'HR',
                           'TB', 'RBI', 'SB', 'CB', 'BB', 'HBP', 'IBB', 'SO', 'DP', 'SH', 'SF', 'AVG',
                           'OBP', 'SLG', 'OPS', 'wOBA', 'WRC+']

        return team_df

    def crawl_team_rank(self, year=1982):
        """
            Crawl KBO team rank of the given year.
                :param int year: A year to crawl. Default is 1982. (KBO launch year)
                :return: (DataFrame) A DataFrame with crawled rank.
        """

        rank_df = pd.DataFrame()

        # Statiz does not support team rank. So use KBO official website instead.
        url = 'https://www.koreabaseball.com/TeamRank/TeamRank.aspx'
        xpath = '//*[@id="cphContents_cphContents_cphContents_ddlYear"]'

        self.driver.get(url)
        select = Select(self.driver.find_element_by_xpath(xpath))
        select.select_by_value(str(year))
        time.sleep(3)

        page = BeautifulSoup(self.driver.page_source, 'lxml')
        trs = page.findAll('tr')

        count = 1
        print('Now Crawling : {0} team rank'.format(year))

        for tr in trs:
            utils.progress_bar(count, len(trs))
            count += 1

            tr = tr.text.strip().replace('\n', ' ')
            tr = pd.Series(tr.split())

            if len(tr) != 12:
                continue

            rank_df = rank_df.append(tr, ignore_index=True)

        rank_df.columns = rank_df.iloc[0]
        rank_df.drop(0, axis=0, inplace=True)
        rank_df['Season'] = year

        return rank_df

    def crawl_rename(self):
        """
            Crawl the players who change their name.

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
    FILE_PATH2 = r'D:\IT\mywork\Project\KBO-Analysis\dataset\kbo_pitcher.xlsx'
    FILE_PATH3 = r'D:\IT\mywork\Project\KBO-Analysis\dataset\kbo_team.xlsx'
    FILE_PATH4 = r'D:\IT\mywork\Project\KBO-Analysis\dataset\kbo_team_rank.xlsx'
    FILE_PATH5 = r'D:\IT\mywork\Project\KBO-Analysis\dataset\rename.xlsx'
    DRIVER_PATH = r'D:\IT\mywork\chromedriver.exe'

    batter = pd.DataFrame()
    pitcher = pd.DataFrame()
    team = pd.DataFrame()
    rank = pd.DataFrame()
    sc = StatizCrawler(DRIVER_PATH)

    for year in range(1982, 2021):
        batter = batter.append(sc.crawl_player(year, 'B'), ignore_index=True)
        pitcher = pitcher.append(sc.crawl_player(year, 'P'), ignore_index=True)
        team = team.append(sc.crawl_team(year), ignore_index=True)
        rank = rank.append(sc.crawl_team_rank(year), ignore_index=True)

    rename = sc.crawl_rename()

    del sc

    batter.to_excel(FILE_PATH1, encoding='utf-8', index=False)
    pitcher.to_excel(FILE_PATH2, encoding='utf-8', index=False)
    team.to_excel(FILE_PATH3, encoding='utf-8', index=False)
    rank.to_excel(FILE_PATH4, encoding='utf-8', index=False)
    rename.to_excel(FILE_PATH5, encoding='utf-8', index=False)
