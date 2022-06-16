import re
import os
import json
import sqlite3
import shutil
import time
from bs4 import BeautifulSoup
import requests
import tkinter as tk
import tkinter.scrolledtext

PACK_DESTINATION = r'packs'
PACK_NAME = r'pack'

HELP_TEXT = r"""
Instructions:
1. Enter the path to your beatoraja songdb and the url of a table.
2. Click "Find Table Songs in DB".
3. Click "Make Table Pack"
""".strip()

DETAILS_TEXT = r"""
What the buttons do

"Find Table Songs in DB":
- This takes the list of charts from the table, and searches for them in the beatoraja songdb.
- If the chart is in the songdb, and the bms file is indeed present in your PC, it internally records down the path to that bms.
- Finally, it lists all of the table charts that it could not find in the beatoraja songdb (including those that are in the songdb, but are not present on disk).

"Make Table Pack":
- Using the paths it has internally recorded down, it copies all of the bms folders to a new folder in the "pack" folder. This can take a while to complete.
""".strip()

    
def retrieve_url(con, url):
    try:
        req = requests.get(url)
    except Exception as e:
        con.text_print(e)
        con.text_print('Unable to access url: %s' % url)
        return None
    
    if req.status_code != 200:
        con.text_print('Unable to access url %s: http status code %d' % (url, req.status_code))
        return None
    return req.text
    
def load_table(con, table_url):
    con.text_print('Retrieving table: %s' % table_url)
    html_text = retrieve_url(con, table_url)
    if html_text == None:
        return
        
    soup = BeautifulSoup(html_text, "html.parser")
    tag = soup.find('meta', {'name':'bmstable'})
    if tag == None or not tag.has_key('content'):
        con.text_print('Unable to retrieve table: meta tag not found')
        return
        
    header_url = tag['content']
    header_url = requests.compat.urljoin(table_url, header_url)
    
    header_text = retrieve_url(con, header_url)
    if header_text == None:
        con.text_print('Unable to retrieve header json for table')
        return
    header_json = json.loads(header_text)
    
    symbol = header_json['symbol']
    level_order = header_json.get('level_order', None)
    data_url = header_json['data_url']
    data_url = requests.compat.urljoin(table_url, data_url)
    data_text = retrieve_url(con, data_url)
    if data_text == None:
        con.text_print('Unable to retrieve data json for table')
        return
        
    data_json = json.loads(data_text)
    songs = [(x['md5'], x['title'], x['level']) for x in data_json]
    
    return symbol, level_order, songs
    
    
def load_table_songs(table_json_file):
    with open(table_json_file, encoding='utf-8') as f:
        data = json.loads(f.read())
    songs = [(x['md5'], x['title'], x['level']) for x in data]
    return songs
    
def make_pack(con, folder, packname, final_path_list):
    pack_path = r'%s\%d_%s' % (folder, int(time.time()), packname)
    try:
        os.makedirs(pack_path)
    except:
        pass
    
    target_names = {}
    for path in final_path_list:
        name = os.path.basename(path)
        if name in target_names:
            name = os.path.basename(parent) + '_' + name
        while name in target_names:
            name = '%s%d'%(name, random.randrange(0,10))
        
        target_names[name] = path
        
    target_names = list(target_names.items())
    target_names.sort(key = lambda x:x[-1])
    
    con.text_print('Creating pack in %s...' % pack_path)
        
    for index, value in enumerate(target_names):
        name, path = value
        con.log_info('COPYING (%d/%d): %s -> %s' % (index+1, len(target_names), path, r'%s\%s'%(pack_path, name)))
        shutil.copytree(path, r'%s\%s'%(pack_path, name))
        
    con.text_print('Pack created in: %s' % pack_path)
    
def sort_key(title, level, level_order):
    default_index = 0 if level_order == None else len(level_order)
    m = re.search(r'\d+', level)
    if m == None:
        key = (default_index, level)
    else:
        st, ed = m.span()
        key = (default_index, level[:st], int(level[st:ed]), level[ed:])
        
    if level_order != None and level in level_order:
        key = (level_order.index(level),)
        
    return (key, title)
    
def compute_path_list(con, songdb_path, table_url):
    if not os.path.isfile(songdb_path):
        con.text_print('songdb not found at %s' % songdb_path)
        return
    conn = sqlite3.connect(songdb_path)
    cur = conn.cursor()
    cur.execute('SELECT * FROM song')
    DB_HEADERS = {x[0]:i for i,x in enumerate(cur.description)}

    def find_song_in_database(md5):
        cur.execute('SELECT * FROM song WHERE md5=?', (md5,))
        rows = cur.fetchall()
        return rows
        
    def find_songs_in_database(md5s):
        statement = 'SELECT * FROM song WHERE md5 IN (%s)' % ','.join(['?']*len(md5s))
        cur.execute(statement, (md5s))
        rows = cur.fetchall()
        return rows

    path_songs = {}
    #songs = load_table_songs(TABLE_JSON)
    table_data = load_table(con, table_url)
    if table_data == None: return
    symbol, level_order, songs = table_data
    
    song_hashes = [h for h, s, l in songs]
    song_info = {h:('%s%s'%(symbol,level),title) for h, title, level in songs}
    con.text_print('%d unique charts in table (%d before removing dupes).' %(len(song_info), len(songs)))
    
    chunksize = 900
    for hash_group in (song_hashes[i:i+chunksize] for i in range(0,len(songs),chunksize)):
        #print(len(hash_group))
        rows = find_songs_in_database(hash_group)
        for row in rows:
            songpath = row[DB_HEADERS['path']]
            if not songpath or not os.path.isfile(songpath):
                continue
            dirname = os.path.dirname(songpath)
            if dirname not in path_songs: path_songs[dirname] = []
            path_songs[dirname].append(row[DB_HEADERS['md5']])
        #print(l, h, s)
    
    hashes = {h for h,s,l in songs}
    original_num_hashes = len(hashes)
    
    path_songs = [(set(hs),path) for path,hs in path_songs.items()]
    
    path_songs.sort(key=lambda x : -len(x[0]))
    
    final_path_list = []
    for hs, path in path_songs:
        if hs.intersection(hashes):
            hashes.difference_update(hs)
            final_path_list.append(path)
    
    missing_hashes = list(hashes)
    sort_keys = {h:sort_key(title, level, level_order) for h, title, level in songs}
    #print(sort_keys)
    missing_hashes.sort(key=lambda h : sort_keys[h])
    if len(missing_hashes) > 0:
        con.log_info('Missing charts:')
        for h in missing_hashes:
            level, title = song_info[h]
            con.log_info('%s %s (%s)' % (level, title, h), False)
        con.log_info('^ %d missing charts.' % len(missing_hashes))
    else:
        con.log_info('No missing charts.')
    
    con.text_print('%d/%d charts found in song database.' % (original_num_hashes - len(hashes), original_num_hashes))
    con.text_print('%d bms folders used for %d charts.' % (len(final_path_list), original_num_hashes - len(hashes)))
    
    #for path in final_path_list: print(path)
    return final_path_list
    
def find_table_songs(con):
    con.disable_buttons()
    con.text_clear()
    songdb_path = con.songdb_path_box.get()
    table_url = con.table_url_box.get()
    if not songdb_path:
        con.text_print('Enter songdb path!')
        con.enable_buttons()
        return
    if not table_url:
        con.text_print('Enter table url!')
        con.enable_buttons()
        return
        
    final_path_list = compute_path_list(con, songdb_path, table_url)
    con.set_final_path_list(final_path_list, songdb_path, table_url)
    con.enable_buttons()
    
def make_table_pack(con):
    con.disable_buttons()
    con.text_clear()
    final_path_list = con.get_final_path_list()
    if final_path_list == None:
        con.text_print('Click "Find Table Songs in DB" first.')
        con.enable_buttons()
        return
    
    make_pack(con, PACK_DESTINATION, PACK_NAME, final_path_list)
    con.enable_buttons()
    
    
class MainController(object):

    def set_final_path_list(self, value, songdb_path, table_url):
        self._final_path_list = value
        self._prev_songdb_path = songdb_path
        self._prev_table_url = table_url

    def get_final_path_list(self):
        if self.songdb_path_box.get() != self._prev_songdb_path or self.table_url_box.get() != self._prev_table_url:
            return None
        return self._final_path_list

    def __init__(self):
        self._final_path_list = None
        self._prev_songdb_path = None
        self._prev_table_url = None
    
        self.root = tk.Tk()
        self.root.title("Table Pack Maker")
        self.root.resizable(False, False)
        
        self.pframe = tk.Frame(self.root)
        self.pframe.grid(row=0, column=0)
        #self.pframe.grid_propagate(False)

        tk.Label(self.pframe, text="Enter beatoraja songdb path here",
            width=30, height=1).grid(row=1, columnspan=2)
        
        self.songdb_path_box = tk.Entry(self.pframe, width=70)
        self.songdb_path_box.grid(row=2, columnspan=2)
            
        tk.Label(self.pframe, text="Enter table URL here",
            width=30, height=1).grid(row=3, columnspan=2)
        
        self.table_url_box = tk.Entry(self.pframe, width=70)
        self.table_url_box.grid(row=4, columnspan=2)
       
        tk.Label(self.pframe, text="Results",
            width=30, height=1).grid(row=5, columnspan=2)
        
        self.text_box = tk.scrolledtext.ScrolledText(self.pframe, width=100, height=6, state=tk.DISABLED)
        self.text_box.grid(row=6, columnspan=2)
        self.text_print(HELP_TEXT)
        
        tk.Label(self.pframe, text="Details",
            width=30, height=1).grid(row=7, columnspan=2)
        
        self.details_box = tk.scrolledtext.ScrolledText(self.pframe, width=100, height=20, state=tk.DISABLED)
        self.details_box.grid(row=8, columnspan=2)
        self.log_info(DETAILS_TEXT)
        
        
        self.btn1 = tk.Button(self.pframe, text="Find Table Songs in DB", width=30, height=2, 
            command=lambda:find_table_songs(self))
        self.btn1.grid(row=0, column=0)
        self.btn2 = tk.Button(self.pframe, text="Make Table Pack", width=30, height=2, 
            command=lambda:make_table_pack(self))
        self.btn2.grid(row=0, column=1)
            
    def disable_buttons(self):
        self.btn1['state'] = tk.DISABLED
        self.btn2['state'] = tk.DISABLED
        
    def enable_buttons(self):
        self.btn1['state'] = tk.NORMAL
        self.btn2['state'] = tk.NORMAL
        
    def text_print(self, text, refresh=True):
        self.text_box.configure(state=tk.NORMAL)
        self.text_box.insert(tk.END, text)
        self.text_box.insert(tk.END, '\n')
        self.text_box.see(tk.END)
        self.text_box.configure(state=tk.DISABLED)
        if refresh: self.root.update()
        
    def text_clear(self):
        self.text_box.configure(state=tk.NORMAL)
        self.text_box.delete(1.0, tk.END)
        self.text_box.configure(state=tk.DISABLED)
        self.details_box.configure(state=tk.NORMAL)
        self.details_box.delete(1.0, tk.END)
        self.details_box.configure(state=tk.DISABLED)
        
    def log_info(self, text, refresh=True):
        self.details_box.configure(state=tk.NORMAL)
        self.details_box.insert(tk.END, text)
        self.details_box.insert(tk.END, '\n')
        self.details_box.see(tk.END)
        self.details_box.configure(state=tk.DISABLED)
        if refresh: self.root.update()
        
    def start(self):
        self.root.mainloop()
        
def main():
    main_controller = MainController()
    main_controller.start()
    
if __name__ == '__main__':
    main()
    