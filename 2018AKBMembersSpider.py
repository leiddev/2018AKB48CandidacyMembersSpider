import os
import requests
from pyquery import PyQuery as pq
import re
import pandas
#import urllib3
from requests.exceptions import SSLError
#urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  #for request.get(..., verify = False)

HEADERS = {'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'}
INDEX_URL = 'https://www.akb48.co.jp/sousenkyo53rd/candidate'
DETAIL_URL = 'https://www.akb48.co.jp/sousenkyo53rd/candidate_detail'
GROUPS = ('akb', 'ske', 'nmb', 'hkt', 'ngt', 'stu', 'jkt', 'bnk', 'tpe')
PHOTO_DIR = 'photo'                     #保存官方照片的文件夹
POSTER_DIR = 'poster'                   #保存海报的文件夹
MEMBER_INFO_FILE = 'member_info.xlsx'   #保存成员信息的文件

def mkdir(path):
    path = path.strip().rstrip(os.path.sep)
    if not os.path.exists(path):
        os.makedirs(path) 
        return True
    else:
        return False

def get_resource(url, params):
    try:
        r = requests.get(url, headers = HEADERS, params = params)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        print('URL: ' + r.url)
    except requests.exceptions.SSLError:
        print('SSL Error, retry: ' + r.url)
        r = get_resource(url, params)
    except Exception as e:
        print(e)
        r = None
    finally:
        return r

def save_file_from_url(url, path):
    if os.path.exists(path):
        print('File already exists: ' + path)
        return
    r = get_resource(url, None)
    if r is None:
        print('Failed to get file: ' + url)
        return
    with open(path, 'wb') as f:
        f.write(r.content)
        print('Save file: ' + path)

def save_member_photo(url, name):
    photo_name = name + '.jpg'
    photo_path = '.' + os.path.sep + PHOTO_DIR + os.path.sep + photo_name
    save_file_from_url(url, photo_path)

def save_member_poster(url, name):
    photo_name = name + '.jpg'
    photo_path = '.' + os.path.sep + POSTER_DIR + os.path.sep + photo_name
    save_file_from_url(url, photo_path)

def parse_index_page(group, list):
    r = get_resource(INDEX_URL, {'group' : group})
    if r is None:
        print('Failed to get %s group info' % group.upper())
        return
    doc = pq(r.text)
    teams = doc('.teamBlock.%s' % group).items()
    for team in teams:
        members = team('li').items()
        for member in members:
            info = {
                'id' : member.find('a').attr('href').split('=')[-1],
                'name' : member.find('.name').text().split('／')[0],
                'date' : member.find('.date').text(),               #立候补日期时间
                'commitment' : member.find('.commit span').text(),  #目标
                'photo' : member.find('img').attr('src'),           #官方照片链接
            }
            team_list = [team.text() for team in member.find('.team').items()]
            info['team'] = team_list[0]     #所属Team
            if len(team_list) > 1:          #兼任Team
                info['concurrent'] = team_list[1]
            else:
                info['concurrent'] = '-'
            print(info)
            list.append(info)

def parse_detail_page(id, list):
    res = get_resource(DETAIL_URL, {'id' : id})
    if res is None:
        print('Failed to get detail page, id = ' + id)
        return
    re_pattern = re.compile(r'</li>\s+<li>:\s</li>\s+<li>(.*?)</li>', re.S)
    result = re.findall(re_pattern, res.text)
    doc = pq(res.text)
    info = {
        'id' : id,
        'name' : doc('.profileTxt h4').text().strip().split('／')[0],
        'name_alpha' : doc('.alp').text().strip(),              #字母拼写
        'name_kana' : doc('.kana').text().strip(),              #片假名
        'early_result' : doc('.date').text().split('：')[-1],   #速报结果
        'result' : doc('.result').text().split('：')[-1],       #开票结果
        'commitment' : doc('.commit p').text().split('\n')[0].split('：')[-1],   #目标
        'poster' : doc('.poster img').attr('src').split('?')[0],    #官方海报链接
        'group' : result[0].strip(),        #所属group
        'debut' : result[1].strip(),        #出道期数
        'nickname' : result[2].strip(),     #昵称
        'birthday' : result[3].strip(),     #出生日期
        'homeplace' : result[4].strip(),    #出生地
        'blood' : result[5].strip(),        #血型
    }
    if info['result'] == '':
        info['result'] = '圏外'
    past_results = {                        #過去選抜総選挙結果
        '2017' : result[6].strip(),
        '2016' : result[7].strip(),
        '2015' : result[8].strip(),
        '2014' : result[9].strip(),
        '2013' : result[10].strip(),
        '2012' : result[11].strip(),
        '2011' : result[12].strip(),
        '2010' : result[13].strip(),
        '2009' : result[14].strip(),
    }
    info['past_results'] = past_results
    print(info)
    list.append(info)

def merge_list(list1, list2, output):
    for a in list1:
        for b in list2:
            if a['id'] == b['id']:
                info = {
                    'name' : b['name'],
                    'name_alpha' : b['name_alpha'],
                    'name_kana' : b['name_kana'],
                    'nickname' : b['nickname'],
                    'birthday' : b['birthday'],
                    'homeplace' : b['homeplace'],
                    'blood' : b['blood'],
                    'team' : a['team'],
                    'concurrent' : a['concurrent'],
                    'debut' : b['debut'],
                    'receipt_date' : a['date'],
                    'commitment' : b['commitment'],
                    'early_result' : b['early_result'],
                    'result' : b['result'],
                    '2017' : b['past_results']['2017'],
                    '2016' : b['past_results']['2016'],
                    '2015' : b['past_results']['2015'],
                    '2014' : b['past_results']['2014'],
                    '2013' : b['past_results']['2013'],
                    '2012' : b['past_results']['2012'],
                    '2011' : b['past_results']['2011'],
                    '2010' : b['past_results']['2010'],
                    '2009' : b['past_results']['2009'],
                }
                output.append(info)
                break
        else:
            print('Can not find %s in list2' % a['name'])

def save_data_to_excel(data, file_name):
    columns = [key for key,value in data[0].items()]
    df = pandas.DataFrame(data)
    df.to_excel(file_name, columns = columns, index = False)
    print('Save file: ' + file_name)

def main():
    member_list = []
    member_list_detail = []
    member_list_final = []
    mkdir(PHOTO_DIR)
    mkdir(POSTER_DIR)
    for group in GROUPS:
        parse_index_page(group, member_list)
    for member in member_list:
        save_member_photo(member['photo'], member['name'])
    for member in member_list:
        parse_detail_page(member['id'], member_list_detail)
    for member in member_list_detail:
        save_member_poster(member['poster'], member['name'])
    merge_list(member_list, member_list_detail, member_list_final)
    save_data_to_excel(member_list_final, MEMBER_INFO_FILE)

if __name__ == '__main__':
    main()