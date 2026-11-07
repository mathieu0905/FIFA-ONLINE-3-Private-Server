"""Reviewed senior-career facts for legacy IDs missing from Nexon's exact-ID metadata.

Rows: installed club ID, joining year, ending year, loan flag.
No player/club IDs or joining years are inferred from names or observation dates.
Birth dates are checked against every installed card of the identity before applying.
"""
DATA = {
    2769: ('1982-08-24','Jose Bosingwa','Jos%C3%A9_Bosingwa',[(1898,2000,2003,0),(236,2003,2008,0),(5,2008,2012,0),(15,2012,2013,0),(436,2013,2015,0),(436,2016,2016,0)]),
    51123: ('1982-11-22','Mathieu Bodmer','Mathieu_Bodmer',[(210,2000,2003,0),(65,2003,2007,0),(66,2007,2010,0),(73,2010,2013,0),(1819,2013,2013,1),(72,2013,2017,0),(62,2017,2017,0),(1816,2017,2020,0)]),
    135423: ('1980-06-24','Cicinho','Cicinho',[(1035,2001,2003,0),(517,2001,2001,1),(598,2004,2005,0),(243,2006,2007,0),(52,2007,2012,0),(598,2010,2010,1),(483,2011,2011,1),(111057,2012,2013,0)]),
    141645: ('1979-09-11','Eric Abidal','Eric_Abidal',[(69,2000,2002,0),(65,2002,2004,0),(66,2004,2007,0),(241,2007,2013,0),(69,2013,2014,0),(280,2014,2014,0)]),
    163423: ('1986-05-11','Abou Diaby','Abou_Diaby',[(57,2004,2006,0),(1,2006,2015,0),(219,2015,2017,0)]),
    199835: ('1987-05-10','Emmanuel Emenike','Emmanuel_Emenike',[(112122,2009,2011,0),(326,2011,2011,0),(100767,2011,2013,0),(326,2013,2017,0),(19,2016,2016,1),(280,2017,2018,0),(472,2018,2018,1),(681,2019,2019,0)]),
    204550: ('1990-05-19','Victor Ibarbo','V%C3%ADctor_Ibarbo',[(101100,2008,2011,0),(1842,2011,2017,0),(52,2015,2015,1),(1795,2015,2016,1),(101100,2016,2016,1),(1884,2016,2017,1),(101099,2023,2024,0)]),
    36: ('1971-11-03', 'Dwight Yorke', 'Dwight_Yorke', [(2,1989,1998,0),(11,1998,2002,0),(3,2002,2004,0),(88,2004,2005,0),(111400,2005,2006,0),(106,2006,2009,0)]),
    239: ('1971-10-15', 'Andy Cole', 'Andy_Cole', [(1,1989,1992,0),(144,1991,1991,1),(1919,1992,1992,1),(1919,1992,1993,0),(13,1993,1995,0),(11,1995,2001,0),(3,2001,2004,0),(144,2004,2005,0),(10,2005,2006,0),(1790,2006,2007,0),(88,2007,2007,1),(106,2007,2008,0),(1796,2008,2008,1),(14,2008,2008,0)]),
    245: ('1975-01-21', 'Nicky Butt', 'Nicky_Butt', [(11,1992,2004,0),(13,2004,2010,0),(88,2005,2006,1)]),
    249: ('1977-01-21', 'Phil Neville', 'Phil_Neville', [(11,1994,2005,0),(7,2005,2013,0)]),
    53019: ('1965-10-31', 'Denis Irwin', 'Denis_Irwin', [(8,1983,1986,0),(1920,1986,1990,0),(11,1990,2002,0),(110,2002,2004,0)]),
    230024: ('1957-01-11', 'Bryan Robson', 'Bryan_Robson', [(109,1975,1981,0),(11,1981,1994,0),(12,1994,1997,0)]),
    230026: ('1940-02-24', 'Denis Law', 'Denis_Law', [(1939,1956,1960,0),(10,1960,1961,0),(54,1961,1962,0),(11,1962,1973,0),(10,1973,1974,0)]),
    # Old display names transpose Yang Chen and misspell Li Jinyu; DOB and nationality,
    # not the spelling alone, establish the reviewed identity. Display names stay intact.
    999800: ('1969-11-06', 'Fan Zhiyi', 'Fan_Zhiyi', [(110955,1994,1998,0),(1799,1998,2001,0),(180,2001,2002,0),(1961,2002,2003,0)]),
    999801: ('1970-05-09', 'Hao Haidong', 'Hao_Haidong', [(110954,1997,2004,0),(1794,2005,2006,0)]),
    999802: ('1974-01-17', 'Yang Chen', 'Yang_Chen_(footballer,_born_1974)', [(111768,1993,1997,0),(1824,1998,2002,0),(110329,2002,2003,0),(111773,2003,2005,0)]),
    999803: ('1971-01-26', 'Li Ming (1971)', 'Li_Ming_(footballer,_born_1971)', [(110954,1989,2005,0)]),
    999804: ('1977-07-06', 'Li Jinyu', 'Li_Jinyu', [(111770,1998,2003,0),(1823,1999,1999,1),(111724,2004,2010,0)]),
    999805: ('1968-08-26', 'Ou / Qu Chuliang', 'Qu_Chuliang', [(110955,1998,1999,0),(112165,2004,2004,0)]),
    999806: ('1975-02-14', 'Xie Hui', 'Xie_Hui_(footballer)', [(110955,1994,2000,0),(1826,2000,2002,0),(110955,2002,2002,1),(165,2002,2003,0),(112165,2003,2004,0),(110955,2005,2008,0),(492,2008,2008,1)]),
    # Birth year varies across biographical sources (1959/1962); installed legacy
    # card uses 1963. This is an explicit name + country + month/day exception;
    # the installed birthday is guarded and is not corrected by this history patch.
    999600: ('1963-11-14', 'Piyapong Pue-on', 'Piyapong_Pue-on', [(982,1984,1986,0)]),
    999601: ('1973-08-11', 'Kiatisuk Senamuang', 'Kiatisuk_Senamuang', [(1939,1999,2000,0)]),
    174675: ('1985-12-10', 'Le Cong Vinh', 'L%C3%AA_C%C3%B4ng_Vinh', [(112444,2013,2013,1)]),
    999500: ('1972-04-20', 'Le Huynh Duc', 'L%C3%AA_Hu%E1%BB%B3nh_%C4%90%E1%BB%A9c', [(112165,2001,2001,0)]),
}

# Explicit mapping between a verified Nexon career name and this client's historic ID.
EXACT_CLUB_ALIASES = {'디나모 모스크바': (312, '莫斯科迪纳摩'), 'TSV 1860 뮌헨': (33, '慕尼黑1860')}

EXTRA_SOURCES = {
    245: ['https://www.uefa.com/news-media/news/01ac-0e6cd0415c08-d679d38b90ed-1000--birmingham-bring-in-butt/'],
    249: ['https://www.manutd.com/en/news/a-to-z-goal-of-the-day-series-n-is-for-phil-neville'],
    53019: ['https://www.uefa.com/uefachampionsleague/news/0187-0e6a4362a085-9dbfe0b9f0f6-1000--wolves-snap-up-united-veteran-irwin/'],
    230026: ['https://www.scottishfootballmuseum.org.uk/exhibitions/hall-of-fame/denis-law/'],
    174675: ['https://www.the-afc.com/en/more/news/sapporo_spell_for_vietnam_star.html'],
    999806: ['https://datencenter.dfb.de/datencenter/personen/hui-xie/spieler'],
    238380: ['https://en.fcdynamo.ru/legend/yashin/'],
}

# These legacy identities have only careers in clubs with no verified installed
# club-ID mapping. Retain evidence and flag the gap; do not give them a nation,
# coaching club, same-name modern club or a made-up ID as a substitute.
UNSUPPORTED_REVIEWS = {
    100: ('Ong_Kim_Swee', ['Malacca','Sarawak','Sabah']),
    101: ('Serbegeth_Singh', ['Johor','Kuala Lumpur','Pahang','Negeri Sembilan','Perak']),
    102: ('Dollah_Salleh', ['Johor','Selangor','Pahang','Malacca','Negeri Sembilan']),
    174673: ('D%C6%B0%C6%A1ng_H%E1%BB%93ng_S%C6%A1n', ['Song Lam Nghe An','Hanoi T&T']),
    174687: ('Nguy%E1%BB%85n_Minh_Ph%C6%B0%C6%A1ng', ['Cang Sai Gon','Dong Tam Long An','SHB Da Nang']),
    174692: ('Ph%E1%BA%A1m_V%C4%83n_Quy%E1%BA%BFn', ['Song Lam Nghe An','Xuan Thanh Sai Gon','Vissai Ninh Binh']),
    174694: ('Phan_V%C4%83n_T%C3%A0i_Em', ['Dong Tam Long An','Navibank Sai Gon','Sai Gon Xuan Thanh']),
    195670: ('L%C3%AA_Ph%C6%B0%E1%BB%9Bc_T%E1%BB%A9', ['Quan khu 5','The Cong','Lam Son Thanh Hoa','Xuan Thanh Sai Gon','Quang Nam','Vissai Ninh Binh','Becamex Binh Duong']),
    195710: ('L%C3%AA_T%E1%BA%A5n_T%C3%A0i', ['Khatoco Khanh Hoa','Hai Phong','Becamex Binh Duong','Hong Linh Ha Tinh','Hanoi']),
    195718: ('V%C5%A9_Nh%C6%B0_Th%C3%A0nh', ['The Cong','Becamex Binh Duong','Vissai Ninh Binh','Hai Phong','Hung Vuong An Giang','XM Fico Tay Ninh','Phu Dong']),
    217970: ('Ph%E1%BA%A1m_Th%C3%A0nh_L%C6%B0%C6%A1ng', ['Hanoi ACB','Hanoi T&T']),
    999501: ('Nguy%E1%BB%85n_H%E1%BB%93ng_S%C6%A1n', ['The Cong','Cong Nhan Bia Do']),
    999502: ('Tr%E1%BA%A7n_C%C3%B4ng_Minh_(footballer,_born_1970)', ['Dong Thap']),
    999602: ('Totchtawan_Sripan', ['Raj-Vithi','Bangkok Bank','Sembawang Rangers','Hoang Anh Gia Lai','BEC Tero Sasana']),
}
