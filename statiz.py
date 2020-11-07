import re
from bs4 import BeautifulSoup
from selenium import webdriver
import pandas as pd


WD_PATH = 'D:/IT/mywork/chromedriver.exe'
OPTIONS = webdriver.ChromeOptions()
OPTIONS.add_argument('--headless')
OPTIONS.add_argument('--no-sandbox')
OPTIONS.add_argument('--disable-dev-shm-usage')
OPTIONS.add_argument('disable-gpu')

driver = webdriver.Chrome(WD_PATH, options=OPTIONS)

XPATH = '//*[@id="mytable"]/tbody'
BASE_URL = 'http://www.statiz.co.kr/stat.php?opt=0&sopt=0&re=0&ys=2020&ye=2020&se=0&te=&tm=&ty=0&qu=auto&' \
           'po=0&as=&ae=&hi=&un=&pl=&da=1&o1=WAR_ALL_ADJ&de=1&lr=0&tr=&cv=&ml=1&sn=1000&si=&cn=1000'

# crawling
driver.get(BASE_URL)
driver.implicitly_wait(5)

html = driver.find_element_by_xpath(XPATH).get_attribute("innerHTML")
page = BeautifulSoup(html, 'html.parser')

driver.close()

# regex
birth_regex = re.compile(r'\d{4}-\d{2}-\d{2}')
name_regex = re.compile(r'\d+(.*\d{2})?')
position_regex = re.compile(r'(1B|2B|3B|SS|C|LF|RF|CF|DH)$')

trs = page.findAll('tr')
df = pd.DataFrame(columns=['name', 'birth', 'team', 'position'])

for tr in trs:
    tmp = tr
    tr = pd.Series(tr.text.strip().replace('\n', '').split(' '))

    if len(tr) == 1:
        continue

    birth = ''.join(birth_regex.findall(tmp.find('a')['href']))
    name = ''.join(name_regex.findall(tr[0]))
    position = ''.join(position_regex.findall(tr[0]))

    team_regex = re.compile(name + '(.*)?' + position)
    team = ''.join(team_regex.findall(tr[0]))

    tr = tr.replace('', pd.NA)
    tr['name'] = name
    tr['birth'] = birth
    tr['team'] = team
    tr['position'] = position

    df = df.append(tr, ignore_index=True).dropna(axis=1)


df.drop([0, 53], axis=1, inplace=True)  # remove useless / duplicate data
df.columns = ['Name', 'Birth', 'Team', 'Position', 'WAR', 'G', 'PA', 'AB', 'R', 'H', '2B', '3B',
              'HR', 'TB', 'RBI', 'SB', 'CB', 'BB', 'HBP', 'IBB', 'SO', 'DP', 'SH', 'SF', 'WPA']

print(df)
