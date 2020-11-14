import re
from bs4 import BeautifulSoup
from selenium import webdriver
import pandas as pd
import utils


class StatizCrawler:
    WEBDRIVER_PATH = 'D:/IT/mywork/chromedriver.exe'
    XPATH = '//*[@id="mytable"]/tbody'

    OPTIONS = webdriver.ChromeOptions()
    OPTIONS.add_argument('--headless')
    OPTIONS.add_argument('--no-sandbox')
    OPTIONS.add_argument('--disable-dev-shm-usage')
    OPTIONS.add_argument('disable-gpu')

    U = 'http://www.statiz.co.kr/stat.php?opt=0&sopt=0&re=0&ys='
    R = '&ye='
    L = '&se=0&te=&tm=&ty=0&qu=auto&po=0&as=&ae=&hi=&un=&pl=&da=1&o1=WAR_ALL_ADJ' \
        '&de=1&lr=0&tr=&cv=&ml=1&sn=1000&si=&cn=500'

    def __init__(self, year):
        self.birth_regex = re.compile(r'\d{4}-\d{2}-\d{2}')
        self.name_regex = re.compile(r'\d+(.*\d{2})?')
        self.position_regex = re.compile(r'(1B|2B|3B|SS|C|LF|RF|CF|DH|P)$')

        self.statiz_df = pd.DataFrame(columns=['name', 'birth', 'team', 'position'])
        self.base_url = self.U + str(year) + self.R + str(year) + self.L

    def crawl(self):
        """
        Crawl KBO Batter records from the Statiz website. (http://www.statiz.co.kr)
            :return: None
        """

        driver = webdriver.Chrome(self.WEBDRIVER_PATH, options=self.OPTIONS)
        driver.get(self.base_url)
        driver.implicitly_wait(5)

        html = driver.find_element_by_xpath(self.XPATH).get_attribute("innerHTML")
        page = BeautifulSoup(html, 'html.parser')
        trs = page.findAll('tr')

        count = 1
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
            tr['name'] = name
            tr['birth'] = birth
            tr['team'] = team
            tr['position'] = position

            self.statiz_df = self.statiz_df.append(tr, ignore_index=True)

        driver.quit()

        return self.statiz_df.dropna(axis=1)


def set_columns(df):
    """
    Rename column names and remove unnecessary columns.
        :param df: A DataFrame
        :return: A DataFrame that columns changed
    """

    df = df.dropna(axis=1).drop([0, 53], axis=1)
    df.columns = ['Name', 'Birth', 'Team', 'Position', 'WAR', 'G', 'PA', 'AB', 'R', 'H', '2B', '3B',
                  'HR', 'TB', 'RBI', 'SB', 'CB', 'BB', 'HBP', 'IBB', 'SO', 'DP', 'SH', 'SF']

    return df


if __name__ == '__main__':
    file_path = 'D:/IT/mywork/kbo_batter.xlsx'
    baseball = pd.DataFrame()

    for year in range(1982, 2021):
        sc = StatizCrawler(year)
        print('Now Scraping : {}'.format(year))
        baseball = baseball.append(sc.crawl(), ignore_index=True)

    baseball = set_columns(baseball)
    print(baseball.head())
    print(baseball.tail())
    baseball.to_excel(file_path, encoding='utf-8', index=False)
