#!/bin/env python3

#
# python-bluetooth-mesh - Bluetooth Mesh for Python
#
# Copyright (C) 2019  SILVAIR sp. z o.o.
#
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#
from functools import lru_cache
import re
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import cmac
from cryptography.hazmat.primitives.ciphers import algorithms, aead, Cipher, modes

import bitstring


def aes_cmac(k, m):
    c = cmac.CMAC(algorithms.AES(k), backend=default_backend())
    c.update(m)
    return c.finalize()


def aes_ccm(k, n, m, a=b'', tag_length=4):
    c = aead.AESCCM(k, tag_length)
    return c.encrypt(n, m, a)

def aes_ccm_decrypt(k, n, m, a=b'', tag_length=4):
    c = aead.AESCCM(k, tag_length)
    return c.decrypt(n, m, a)


def aes_ecb(k, m):
    c = Cipher(algorithms.AES(k), modes.ECB(), backend=default_backend())
    e = c.encryptor()
    return e.update(m) + e.finalize()


def s1(M):
    ZERO = bytes([0] * 16)
    return aes_cmac(ZERO, M)


def k1(N, SALT, P):
    T = aes_cmac(SALT, N)
    return aes_cmac(T, P)


def k2(N, P):
    SALT = s1(b'smk2')
    T = aes_cmac(SALT, N)
    T0 = b''
    T1 = aes_cmac(T, T0 + P + b'\x01')
    T2 = aes_cmac(T, T1 + P + b'\x02')
    T3 = aes_cmac(T, T2 + P + b'\x03')

    k = (T1 + T2 + T3)[-33:]

    n, e, p = bitstring.BitString(k).unpack('pad:1, uint:7, bits:128, bits:128')

    return n, e.bytes, p.bytes


def k3(N):
    SALT = s1(b'smk3')
    T = aes_cmac(SALT, N)
    return aes_cmac(T, b'id64\x01')[-8:]


def k4(N):
    SALT = s1(b'smk4')
    T = aes_cmac(SALT, N)

    k = aes_cmac(T, b'id6\x01')[-1:]

    aid, = bitstring.BitString(k).unpack('pad:2, uint:6')

    return aid

class Key:
    def __init__(self, key, iv_index=0):
        self._key = key
        self._iv_index = iv_index

    @classmethod
    def fromString(cls, s, iv_index=0):
        return cls(bytes.fromhex(s), iv_index)

    @classmethod
    def fromBytes(cls, s, iv_index=0):
        return cls(s, iv_index)

class ApplicationKey(Key):
    def __init__(self, key, iv_index=0):
        Key.__init__(self, key, iv_index)
    
    @property
    @lru_cache(maxsize=1)
    def aid(self):
        return k4(self._key)

class NetworkKey(Key):
    def __init__(self, key, iv_index=0):
        Key.__init__(self, key, iv_index)
        self._nid, self._encryptkey, self._privacykey = self.encryption_keys

    @property
    def nid(self):
        return self._nid

    @property
    def iv_index(self):
        return self._iv_index
    
    @property
    def encrypt_key(self):
        return self._encryptkey
    
    @property
    def privacy_key(self):
        return self._privacykey

    @property
    @lru_cache(maxsize=1)
    def network_id(self):
        return k3(self._key)

    @property
    @lru_cache(maxsize=1)
    def encryption_keys(self):
        return k2(self._key, b'\x00')

    @property
    @lru_cache(maxsize=1)
    def identity_key(self):
        return k1(self._key, s1(b'nkik'), b'id128\x01')

    @property
    @lru_cache(maxsize=1)
    def beacon_key(self):
        return k1(self._key, s1(b'nkbk'), b'id128\x01')
    
    def nounce(self, seq):
        pass
        

class DeviceKey(Key):
    def __init__(self, key):
        Key.__init__(self, key)

class Addr(bytes):
    def __str__(self, sep:str=':'):
        return sep.join(map('{:02x}'.format, self))

    @classmethod
    def from_string(cls, s):
        if isinstance(s, str):
            if re.fullmatch("([0-9a-fA-F]{2}-){5}[0-9a-fA-F]{2}"):
                return cls.fromhex(s.replace('-', ''))
            elif re.fullmatch("([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}"):
                return cls.fromhex(s.replace(':', ''))
            elif re.fullmatch("[0-9a-fA-F]{12}"):
                return cls.fromhex(s)
            else:
                return None
        elif isinstance(s, bytes):
            if len(s) == 6:
                return cls(s)
        
        return None
