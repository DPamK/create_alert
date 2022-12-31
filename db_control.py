import sqlite3

def create_connnect_db(db_path):
    connect = sqlite3.connect(db_path)
    print("open database")
    return connect

def delete_BlankWord(connect,type,source,replace=''):
    if type not in ['delete','insert','special_n','replace']:
        print('请检查type字段')
        return False
    elif type == 'delete' or type == 'special_n':
        if replace != '':
            print('delete 和 speical_n 无法加入 replace')
            return False
    elif type == 'insert' or type == 'replace':
        if replace == '':
            print('insert 和 replace 的 replace 不能为空')
            return False
    cur = connect.cursor()
    cur.execute('DELETE FROM blank_words WHERE type=? AND source=? AND replace=?',(type,source,replace))
    connect.commit()
    print('删除成功')
    return True

def insert_SentitiveWord(connect,word):
    cur = connect.cursor()
    cur.execute('select * from sentitive_words where word=?',(word,))
    if cur.fetchone():
        print('数据已存在')
        return False
    else:
        cur.execute('INSERT INTO sentitive_words(word) VALUES(?)',(word,))
        connect.commit()
        print('添加成功')
        return True

def insert_BlankWord(connect,type,source,replace=''):
    '''
    type:delete,insert,speial_n,replace
    用两个词定位，就一个source，一个replace
    用一个词定位，就定位source
    '''
    if type not in ['delete','insert','special_n','replace']:
        print('请检查type字段')
        return False
    elif type == 'delete' or type == 'special_n':
        if replace != '':
            print('delete 和 speical_n 无法加入 replace')
            return False
    elif type == 'insert' or type == 'replace':
        if replace == '':
            print('insert 和 replace 的 replace 不能为空')
            return False

    cur = connect.cursor()
    cur.execute('select * from blank_words where type=? AND source=? AND replace=?',(type,source,replace))
    if cur.fetchone():
        print('数据已存在')
        return False
    else:
        cur.execute('INSERT INTO blank_words(type,source,replace) VALUES(?,?,?)',(type,source,replace))
        connect.commit()
        print('添加成功')
        return True

def search_type(connect,type):
    cur = connect.cursor()
    cur.execute("SELECT * FROM blank_words WHERE type=?",(type,))
    res = cur.fetchall()
    return res

if __name__=="__main__":
    filiter_db_path = 'database/filiter_db.db'
    connect = create_connnect_db(filiter_db_path)
    
   
    insert_SentitiveWord(connect,'卖淫')

    connect.close()