#
# @author Miroc
# @author Ph4r05
#

from __future__ import print_function
import sqlite3
import re
import csv
import hashlib

leaksFile = '/Volumes/EXTDATA/wifileaks_all.tsv'
connUbeeDB = sqlite3.connect('/Volumes/EXTDATA/ubeekeys.db')

def get_macs(bssid_suffix):
    macs = []
    hex_num = '0x00' + bssid_suffix
    num = int(hex_num, 0)
    if (num == 0):
        return [(0, '000000')]
    for i in range(-10, 11):
        hex_iterated = hex((num + i))[2:]
        hex_iterated_zfilled = hex_iterated.zfill(6)
        macs.append((i, hex_iterated_zfilled))
    return macs

def macstr2s(m):
    return [m[0:2], m[2:4], m[4:6], m[6:8], m[8:10], m[10:12]]

def compute_ssid(mac):
    '''
    Generates SSID from the MAC - reverse engineered from UBEE
    :param mac:
    :return:
    '''
    m = hashlib.md5()
    m2 = hashlib.md5()
    mac = [int(x,16) for x in mac]

    # MAC+hex(UPCDEAULTSSID)
    inp1 = "%2X%2X%2X%2X%2X%2X555043444541554C5453534944\0" % (mac[0], mac[1], mac[2], mac[3], mac[4], mac[5])
    m.update(inp1)
    h1 = [ord(x) for x in m.digest()]

    inp2 = "%.02X%.02X%.02X%.02X%.02X%.02X\0" % (h1[0]&0xf, h1[1]&0xf, h1[2]&0xf, h1[3]&0xf, h1[4]&0xf, h1[5]&0xf)
    m2.update(inp2)
    h2 = [ord(x) for x in m2.digest()]

    return "UPC%d%d%d%d%d%d%d" % (h2[0]%10, h2[1]%10, h2[2]%10, h2[3]%10, h2[4]%10, h2[5]%10, h2[6]%10)

def compute_password(mac):
    '''
    Generates password from the MAC - reverse engineered from UBEE.
    Warning: does not implement profanity detection.
    :param mac:
    :return:
    '''
    m = hashlib.md5()
    m2 = hashlib.md5()
    mac = [int(x,16) for x in mac]

    # MAC+hex(UPCDEAULTPASSPHRASE)
    inp1 = "%2X%2X%2X%2X%2X%2X555043444541554C5450415353504852415345\0" % (mac[0], mac[1], mac[2], mac[3], mac[4], mac[5])
    m.update(inp1)
    h1 = [ord(x) for x in m.digest()]

    inp2 = "%.02X%.02X%.02X%.02X%.02X%.02X\0" % (h1[0]&0xf, h1[1]&0xf, h1[2]&0xf, h1[3]&0xf, h1[4]&0xf, h1[5]&0xf)
    m2.update(inp2)
    h2 = [ord(x) for x in m2.digest()]

    return "%c%c%c%c%c%c%c%c" % (
        (0x41 + ((h2[0]+h2[8]) % 0x1A)),
        (0x41 + ((h2[1]+h2[9]) % 0x1A)),
        (0x41 + ((h2[2]+h2[10]) % 0x1A)),
        (0x41 + ((h2[3]+h2[11]) % 0x1A)),
        (0x41 + ((h2[4]+h2[12]) % 0x1A)),
        (0x41 + ((h2[5]+h2[13]) % 0x1A)),
        (0x41 + ((h2[6]+h2[14]) % 0x1A)),
        (0x41 + ((h2[7]+h2[15]) % 0x1A)))

def gen_ssids(s):
    macs = []
    num = int(''.join(s), 16)
    for i in range(-5, 5):
        hex_iterated = hex((num + i))[2:]
        hex_iterated_zfilled = hex_iterated.zfill(12)
        s = macstr2s(hex_iterated_zfilled)
        ssid = compute_ssid(s)
        macs.append((i, hex_iterated_zfilled, ssid))
    return macs

# Statistics
ubee_count = 0
ubee_24 = 0
ubee_5 = 0
ubee_unknown = 0
collisions_count = 0
total_count = 0
upc_count = 0
ubee_changed_ssid = 0
ubee_no_match = 0
ubee_match = 0
upc_no_match = 0
totalidx = 0
upc_mac_prefixes_counts = {}
use_database_approach = False

res = []

with open(leaksFile) as f:
    reader = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
    for row in reader:
        if len(row)<3: continue
        totalidx += 1

        bssid = row[0]
        ssid = row[1]
        time = row[4]
        #if not re.match(r'^201[6]-', time): continue

        #if ((totalidx % 20000) == 0): print("--Idx: ", totalidx)

        total_count += 1
        s = bssid.split(':')
        isUbee = (s[0] == '64') and (s[1] == '7c') and (s[2] == '34')
        if isUbee:
            ubee_count += 1

        # ssid_no_upc = ssid[3:]
        if re.match(r'^UPC[0-9]{6,9}$', ssid):
            upc_count += 1
            bssid_prefix = s[0] + s[1] + s[2]
            bssid_suffix = s[3] + s[4] + s[5]

            macs = get_macs(bssid_suffix)
            itmap = {}
            for it,mac in macs: itmap[str(mac)] = it

            if bssid_prefix in upc_mac_prefixes_counts:
                upc_mac_prefixes_counts[bssid_prefix] += 1
            else:
                upc_mac_prefixes_counts[bssid_prefix] = 1

            upc_matches = 0

            # Generate SSID in python, without lookup
            computed_ssids = gen_ssids(s)
            for cit, cmac, cssid in computed_ssids:
                if cssid == ssid:
                    # BSSID, it, MAC, SSID
                    shift = cit
                    if shift == -3: ubee_24 += 1
                    elif shift == -1: ubee_5 += 1
                    else: ubee_unknown += 1
                    res.append((bssid, shift, cmac, cssid, ssid))
                    collisions_count += 1
                    upc_matches += 1
                    if isUbee: ubee_match += 1
                    else: print("Got not of UBEE!")

            # Database approach
            if use_database_approach:
                c2 = connUbeeDB.cursor()
                c2.execute('SELECT mac,ssid from wifi where mac IN ("' + ('","'.join(x[1] for x in macs)) + '")')
                dbres = c2.fetchall()
                for r2 in dbres:
                    mac = r2[0]
                    if r2 is None:
                        print("bad mac", mac, bssid_suffix, bssid, ssid)
                        continue
                    gen_mac = r2[0]
                    gen_ssid = 'UPC' + r2[1]
                    if gen_ssid == ssid:
                        # BSSID, it, MAC, SSID
                        shift = int(itmap[str(mac)])
                        if shift == -3: ubee_24 += 1
                        elif shift == -1: ubee_5 += 1
                        else: ubee_unknown += 1
                        res.append((bssid, shift, mac, gen_ssid, ssid))
                        collisions_count += 1
                        upc_matches += 1
                        if isUbee: ubee_match += 1

            # No match - compute
            if upc_matches == 0:
                upc_no_match += 1
                if isUbee: ubee_no_match += 1

        elif isUbee:
            ubee_changed_ssid += 1

for r in res:
    print(r)

print("UPC mac prefixes: ")
for k in upc_mac_prefixes_counts:
    print(" %s: %s" % (k, upc_mac_prefixes_counts[k]))

print("Total count: ", total_count)
print("UPC count: ", upc_count)
print("UBEE count: ", ubee_count)
print("UBEE changed count: ", ubee_changed_ssid)
print("UBEE matches: ", collisions_count)
print("UBEE 2.4: ", ubee_24)
print("UBEE 5.0: ", ubee_5)
print("UBEE unknown: ", ubee_unknown)
print("UBEE no-match: ", ubee_no_match)
print("UBEE match: ", ubee_match)
print("UPC no-match: ", upc_no_match)



