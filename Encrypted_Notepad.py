r"""
Encrypted Notepad

Copyright (c) 2020 by Tetsuya Kaji

This software is licensed by the MIT license.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Except as contained in this notice, the name(s) of the above copyright holders
shall not be used in advertising or otherwise to promote the sale, use or
other dealings in this Software without prior written authorization.

Icon made by Freepik from www.flaticon.com
"""

r"""
To compile, install pyinstaller and run
    pyinstaller Encrypted_Notepad.py --onefile --noconsole --name=enotepad --icon=security.ico --add-data="security.ico;.
On Visual Studio, you may need to add the path to the library explicitly (add the option: --paths=...\bin)
"""


import sys

import tkinter as tk
from tkinter import filedialog
from tkinter import simpledialog
from tkinter.simpledialog import Dialog
from tkinter import messagebox
from tkinter import font
from tkinter import ttk
from tkinter import colorchooser
from tkinter.colorchooser import askcolor

from datetime import datetime

# To create a "generate random string" functionality
import os
import string
from random import *

# To open OnScreen Keyboard on Windows
import platform
import subprocess

# To encrypt / decrypt the files
import base64
from base64 import binascii
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet, InvalidToken

# There are three Reg Ex packages that can be used: Tcl (Tkinter built-in), re (Python built-in), regex (Python package that intend to replace re in the future)
#  - Tcl can do backward search but cannot do symbolic substitution
#  - re can do symbolic substitution but cannot do backward search
#  - regex can do both
# So we go with regex.
import regex as re # This is *different* from 'import re'
import webbrowser # To create a hyperlink to a regex tutorial website

import configparser
import ast


# https://stackoverflow.com/questions/214359/converting-hex-color-to-rgb-and-vice-versa
# https://stackoverflow.com/a/40809696
def hex_to_rgb(hex):
    """Return (red, green, blue) for the color given as #rrggbb."""
    hex = hex.lstrip('#')
    lv = len(hex)
    return tuple(int(hex[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

# 16-bit RGB (each component is max 65535) to hex
# For 8-bit, we need to use '#%02x%02x%02x' % rgb, but we don't need for this
# https://bugs.python.org/issue33289
def rgb16_to_hex(rgb):
    """Return color as #rrggbb for the given color values."""
    return '#%04x%04x%04x' % rgb

# https://stackoverflow.com/questions/596216/formula-to-determine-brightness-of-rgb-color
# On the scale of RGB (0-255 for 8-bit, 0-65535 for 16-bit)
def rgb_to_brightness(rgb):
    return 0.2126*rgb[0] + 0.7152*rgb[1] + 0.0722*rgb[2]

# Hex can be of #ffffffffffff or of #ffffff. For each, this works.
# On the scale of 0.0 - 1.0
def hex_to_brightness(hex):
    return rgb_to_brightness(hex_to_rgb(hex)) / (16**((len(hex)-1)//3)-1)


class ConfigParser2(configparser.ConfigParser):
    def __init__(self, *args, **kwargs):
        configparser.ConfigParser.__init__(self, *args, **kwargs)

    # get with a default value option
    def get2(self, section, option, default):
        if not self.has_section(section):
            self.add_section(section)
        if not self.has_option(section, option):
            self.set(section, option, default)
        return self.get(section, option)

    # getint with a default value option
    # if no section / option, add the default value to self and returns it
    # if an existing option is not of int type, then set it to default and returns it
    def getint2(self, section, option, default):
        if not self.has_section(section):
            self.add_section(section)
        if not self.has_option(section, option):
            self.set(section, option, str(default))
        try:
            return self.getint(section, option)
        except ValueError:
            self.set(section, option, str(default))
            return self.getint(section, option)

    # getboolean with a default value option
    # if no section / option, add the default value to self and returns it
    # if an existing option is not of boolean type, then set it to default and returns it
    def getboolean2(self, section, option, default):
        if not self.has_section(section):
            self.add_section(section)
        if not self.has_option(section, option):
            self.set(section, option, str(default))
        try:
            return self.getboolean(section, option)
        except ValueError:
            self.set(section, option, str(default))
            return self.getboolean(section, option)

    def read(self, file):
        self.config_file = file
        super().read(file)

    def write2(self):
        f = open(self.config_file, 'w')
        self.write(f)
        f.close()


class Notepad(ttk.Frame):
    def __init__(self, *args, cp='', salt=b'salt_', iterations=100000, **kwargs):
        ttk.Frame.__init__(self, *args, **kwargs)
        self.text = tk.Text(self, undo=True, autoseparators=True)
        self.vscroll = ttk.Scrollbar(self, orient='vertical')
        self.hscroll = ttk.Scrollbar(self, orient='horizontal')
        self.menu = tk.Menu(self)
        self.master.config(menu=self.menu)

        self.status = ttk.Frame(self)
        self.status.misc = tk.Label(self.status, bd=1, relief='sunken', text='', anchor='w')
        self.status.misc.grid(row=1, column=0, sticky='sew')
        self.status.cursor = tk.Label(self.status, bd=1, relief='sunken', text='', anchor='w')
        self.status.cursor.grid(row=1, column=1, sticky='sew')
        self.status.count = tk.Label(self.status, bd=1, relief='sunken', text='', anchor='w')
        self.status.count.grid(row=1, column=2, sticky='sew')

        # Evenly space status bars
        self.status.grid_columnconfigure(0, weight=1, uniform='a')
        self.status.grid_columnconfigure(1, weight=1, uniform='a')
        self.status.grid_columnconfigure(2, weight=1, uniform='a')

        self.hscroll.show = lambda: self.hscroll.grid(row=1, column=0, sticky='ew')
        self.hscroll.hide = lambda: self.hscroll.grid_forget()
        self.status.show = lambda: self.status.grid(row=2, column=0, columnspan=2, sticky='esw')
        self.status.hide = lambda: self.status.grid_forget()

        self.text.grid(row=0, column=0, sticky='nesw')
        self.vscroll.grid(row=0, column=1, sticky='nes')
        self.hscroll.show()
        self.status.show()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.vscroll.config(command=self.text.yview)
        self.hscroll.config(command=self.text.xview)
        self.text.configure(yscrollcommand=self.vscroll.set)
        self.text.configure(xscrollcommand=self.hscroll.set)

        # Beware that these hacks do not support direct text/cursor modifications by executing insert(), tag_add('sel'), etc.
        self.text.bind('<KeyRelease>', self._on_change)
        self.text.bind('<ButtonRelease-1>', self._on_change)
        self.text.bind('<B1-Motion>', self._on_change)
        self.text.bind('<<Selection>>', self._on_selection)

        self.fpath = ''         # file path
        self.fname = 'Untitled' # file name
        self.key1 = None        # master key for read-only key encryption
        self.key2 = None        # read-only key for text encryption
        self.salt = salt        # sald for encryption
        self.iter = iterations  # iterations for encryption
        self.text.tag_configure('match', foreground=self.text.tag_cget('sel', 'foreground'), background=self.text.tag_cget('sel', 'background'))
        self.text.tag_configure('find all', background='orange red')
        self.text.tag_raise('sel')

        self.rect_select_on = tk.BooleanVar()
        self.wrap_type = tk.IntVar()
        self.status_on = tk.BooleanVar()

        # use configparser to load settings
        self.cp = cp
        # text format
        self.font = font.Font(
            family=self.cp.get2('settings', 'font', 'Courier New'),
            size=self.cp.getint2('settings', 'size', 10),
            weight='bold' if self.cp.getboolean2('settings', 'bold', False) else 'normal',
            slant='italic' if self.cp.getboolean2('settings', 'italic', False) else 'roman',
            underline=self.cp.getboolean2('settings', 'underline', False),
            overstrike=self.cp.getboolean2('settings', 'strikeout', False)
        )
        # color
        self.text.config(font=self.font,
            foreground=self.cp.get2('settings', 'text_color', self.text.cget('foreground')),
            background=self.cp.get2('settings', 'background_color', self.text.cget('background'))
        )
        self.text.tag_configure('normal', background=self.text.cget('background'))
        # adjust the cursor color
        if rgb_to_brightness(self.winfo_rgb(self.text.cget('background'))) > 0.5: # Bright => Make the cursor black
            self.text.config(insertbackground='black')
        else: # Bright => Make the cursor white
            self.text.config(insertbackground='white')
        # misc
        self.wrap_type.set(self.cp.getint2('settings', 'wrap_type', 0))
        self.status_on.set(self.cp.getboolean2('settings', 'status_bar', True))
        # search settings
        self.fr = self.FindReplace(self,
            ignorecase=self.cp.getboolean2('settings', 'ignore_case', True),
            wholeword=self.cp.getboolean2('settings', 'whole_word', False),
            withinsel=self.cp.getboolean2('settings', 'within_selection', False),
            regexp=self.cp.getboolean2('settings', 'regular_expression', False)
        )
        self.fr.withdraw()
        # recent files
        self.recent_files = ast.literal_eval(self.cp.get2('settings', 'recent_files', '[]'))

        self.menu_file = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label='File', underline=0, menu=self.menu_file)
        self.menu_file.add_command(label='New', underline=0, command=self._on_new_file, accelerator='Ctrl+N')
        self.text.bind('<Control-n>', self._on_new_file)
        self.menu_file.add_command(label='Open...', underline=0, command=self._on_open_file, accelerator='Ctrl+O')
        self.text.bind('<Control-o>', self._on_open_file)
        self.menu_file.add_command(label='Save', underline=0, command=self._on_save_file, accelerator='Ctrl+S')
        self.text.bind('<Control-s>', self._on_save_file)
        self.menu_file.add_command(label='Save As...', underline=5, command=self._on_save_file_as, accelerator='Ctrl+Shift+S')
        self.text.bind('<Control-Shift-s>', self._on_save_file_as)
        self.menu_file.add_separator()
        self.menu_recent = tk.Menu(self.menu_file, tearoff=0)
        self.menu_file.add_cascade(label='Recent Files', menu=self.menu_recent, underline=0)
        for fp in self.recent_files:
            self.menu_recent.add_command(label=fp, command=lambda f=fp: self._on_open_file(fpath=f))
        self.menu_recent.add_separator()
        self.menu_recent.add_command(label='Clear Recent Files', underline=0, command=self._on_clear_recent_files)
        self.menu_file.add_separator()
        self.menu_file.add_command(label='Exit', underline=1, command=self._on_exit, accelerator='Alt+F4')

        self.menu_edit = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label='Edit', underline=0, menu=self.menu_edit)
        self.menu_edit.add_command(label='Undo', underline=0, command=self._on_undo, accelerator='Ctrl+Z')
        self.menu_edit.add_command(label='Redo', underline=0, command=self._on_redo, accelerator='Ctrl+Y')
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label='Cut', underline=2, command=self._on_cut, accelerator='Ctrl+X')
        self.menu_edit.add_command(label='Copy', underline=0, command=self._on_copy, accelerator='Ctrl+C')
        self.menu_edit.add_command(label='Paste', underline=0, command=self._on_paste, accelerator='Ctrl+V')
        self.menu_edit.add_command(label='Delete', underline=2, command=self._on_delete, accelerator='Del')
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label='Find/Replace...', underline=0, command=self._on_find_replace, accelerator='Ctrl+F')
        self.text.bind('<Control-f>', self._on_find_replace)
        self.menu_edit.add_command(label='Find Next', underline=5, command=self._on_find_next, accelerator='F3')
        self.text.bind('<F3>', self._on_find_next)
        self.menu_edit.add_command(label='Find Previous', underline=8, command=self._on_find_previous, accelerator='Shift+F3')
        self.text.bind('<Shift-F3>', self._on_find_previous)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label='Select All', underline=7, command=self._on_select_all, accelerator='Ctrl+A')
        self.menu_edit.add_command(label='Insert Time/Date', underline=5, command=self._on_time_date, accelerator='F5')
        self.text.bind('<F5>', self._on_time_date)
        self.menu_edit.add_command(label='Insert Random String', underline=0, command=self._on_random_string, accelerator='F6')
        self.text.bind('<F6>', self._on_random_string)

        self.menu_format = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label='Format', underline=1, menu=self.menu_format)
        self.menu_wrap = tk.Menu(self.menu_format, tearoff=0)
        self.menu_format.add_cascade(label='Word Wrap', menu=self.menu_wrap, underline=0)
        self.menu_wrap.add_radiobutton(label='None', underline=0, value=0, variable=self.wrap_type, command=self._on_word_wrap)
        self.menu_wrap.add_radiobutton(label='Word Wrap', underline=0, value=1, variable=self.wrap_type, command=self._on_word_wrap)
        self.menu_wrap.add_radiobutton(label='Character Wrap', underline=0, value=2, variable=self.wrap_type, command=self._on_word_wrap)
        self.menu_format.add_command(label='Font/Color...', underline=0, command=self._on_font_color)

        self.menu_view = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label='View', underline=0, menu=self.menu_view)
        self.menu_view.add_checkbutton(label='Status Bar', underline=0, onvalue=1, offvalue=0, variable=self.status_on, command=self._on_statusbar)
        self.menu_view.add_command(label='Minimize', underline=0, command=lambda: self.text.event_generate('<Escape>'), accelerator='Esc')

        self.menu_help = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label='Help', underline=0, menu=self.menu_help)
        self.menu_help.add_command(label='About...', underline=0, command=self._on_about)

        self._on_statusbar()
        self._on_word_wrap()
        self._on_change()

        # Quick file checker of Base64 URL-safe decoding
        self.b64re = re.compile(r'^[A-Za-z0-9_=-]*$')


    def _on_change(self, event=None):
        # Statusbar update 1
        line, char = self.text.index('insert').split('.')
        self.status.cursor.configure(text='Ln %s, Col %d' % (line, int(char)+1))
        # Statusbar update 2
        if self.text.tag_ranges('sel'):
            nchars = len(self.text.get('sel.first', 'sel.last'))
            message = str(nchars) + ' Chars Selected'
        else:
            nchars = len(self.text.get('1.0', 'end-1c'))
            message = str(nchars) + ' Chars Total'
        self.status.count.configure(text=message)
        # Title update
        if self.text.edit_modified():
            root.title('*' + self.fname + ' - Encrypted Notepad')
        elif self.text.cget('state') == 'disabled':
            root.title(self.fname + ' (Read Only) - Encrypted Notepad')
        else:
            root.title(self.fname + ' - Encrypted Notepad')

    def _on_selection(self, event=None):
        self.text.tag_remove('normal', '1.0', 'end')
        # apply 'tag_add' to all newline characters in selection
        n_lines = self.text.index('end-1c').split('.')[0]
        for i in range(int(n_lines)):
            line_end_index = '%d.end' % (i + 1)
            self.text.tag_add('normal', line_end_index, line_end_index+'+1c')

    def _update_recent_files(self, fpath):
        # If fpath exists in the current recent files, delete it
        try:
            index = self.recent_files.index(fpath)
            self.recent_files.pop(index)
            self.menu_recent.delete(index)
        except ValueError:
            pass
        # Add fpath to the last of recent files
        self.recent_files.insert(0, fpath)
        self.menu_recent.insert_command(0, label=fpath, command=lambda f=fpath: self._on_open_file(fpath=f))
        # If recent files exceed 5, delete one
        index = len(self.recent_files)
        if index > 5:
            self.menu_recent.delete(index-1)
            self.recent_files.pop(index-1)
        self.cp.set('settings', 'recent_files', str(self.recent_files))

    def _on_clear_recent_files(self):
        index = len(self.recent_files)
        if index > 0:
            self.menu_recent.delete(0, index-1)
            self.recent_files = []
            self.cp.set('settings', 'recent_files', str(self.recent_files))

    def _on_new_file(self, event=None):
        if self.text.edit_modified():
            ans = tk.messagebox.askyesnocancel('Encrypted Notepad', 'Do you want to save changes to ' + self.fname + '?')
            if ans: # Yes
                if not self._on_save_file(): # If the user cancels saving, do not open a new text
                    return
            elif ans is None: # Cancel => Return to window
                return
        self.fpath = ''
        self.fname = 'Untitled'
        self.key1 = None
        self.key2 = None
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        self.text.edit_reset()
        self.text.focus_set()
        self.text.edit_modified(False)
        self._on_change()

    # Read-only password implementation
    def _on_open_file(self, event=None, fpath=None):
        if self.text.edit_modified():
            ans = tk.messagebox.askyesnocancel('Encrypted Notepad', 'Do you want to save changes to ' + self.fname + '?')
            if ans: # Yes
                if not self._on_save_file(): # If the user cancels saving, do not open file and return to window
                    return
            elif ans is None: # Cancel => Return to window
                return
        if fpath is None:
            fpath = tk.filedialog.askopenfilename(filetypes=(('Text Documents (*.txt)','*.txt'),('All Files (*.*)','*.*')))
        if fpath == '': # Cancel
            return
        fname = os.path.basename(fpath)
        try:
            file = open(fpath, 'r') # Open the file in the read mode
            text = file.read()
            file.close()
        except IOError:
            tk.messagebox.showerror(title='Encrypted Notepad', message='I/O error. Could not open ' + fname)
            try:
                index = self.recent_files.index(fpath)
                self.recent_files.pop(index)
                self.menu_recent.delete(index)
            except ValueError:
                pass
            return
        else:
            file.close()
        try:
            # If the length of the text is not a multiple of 4, then not encoded
            if len(text) % 4 != 0:
                raise

            # If it does not contain one and only one separator '====', then not encoded (by this program)
            # If the second part contains characters other than allowed in URL-safe Base64, then not encrypted
            texts = text.rsplit('====')
            if len(texts) != 2 or not self.b64re.fullmatch(texts[1]):
                raise

            # We can also check if texts[0] contains other characters, or the lengths of texts[0] and texts[1] are
            # multiples of 4, etc. But I suspect there won't be practically relevant cases where these are helpful.

            pwd = EnterPasswordDialog(self, fname=fname).result
            if pwd is None: # Cancel => Stop opening file and return to window
                return

            kdf = PBKDF2HMAC(algorithm=hashes.SHA256(),length=32,salt=self.salt,iterations=self.iter,backend=default_backend())
            key = base64.urlsafe_b64encode(kdf.derive(pwd.encode())) # Can only use kdf once
            if pwd == '': # OK with no input => Try Read-Only, otherwise Open file without decryption
                key1 = None
                try:
                    text = Fernet(key).decrypt(texts[0].encode()).decode()
                    key2 = key
                    read_only = True
                except InvalidToken: # If Read-Only with no password fails, open without decryption
                    key2 = None
                    read_only = False
                except ImportError:
                    tk.messagebox.showerror(title='Encrypted Notepad', message='Some dlls are missing. Use "--path=...bin" option in Pyinstaller to explicitly feed the dlls.')
            else:
                try:
                    key2 = Fernet(key).decrypt(texts[1].encode())
                    text = Fernet(key2).decrypt(texts[0].encode()).decode()
                    key1 = key
                    read_only = False
                except InvalidToken:
                    try:
                        text = Fernet(key).decrypt(texts[0].encode()).decode()
                        key1 = None
                        key2 = key
                        read_only = True
                    except InvalidToken:
                        tk.messagebox.showerror(title='Encrypted Notepad', message='Decryption failed. Could not open ' + fname)
                        return
                except ImportError:
                    tk.messagebox.showerror(title='Encrypted Notepad', message='Some dlls are missing. Use "--path=...bin" option in Pyinstaller to explicitly feed the dlls.')

        except:
            # If it throws an error, open the file as is
            key1 = None
            key2 = None
            read_only = False

        self.fpath = fpath
        self.fname = fname
        self.key1 = key1
        self.key2 = key2
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        self.text.insert('end', text)
        self.text.edit_reset() # reset undo stack
        self.text.focus_set() # focus set on the text editor
        self.text.mark_set('insert', '1.0') # bring set cursor to the beginning of file
        self.text.edit_modified(False)
        if read_only:
            self.text.configure(state='disabled')
        self._on_change()
        self._update_recent_files(fpath)


    # Read-only password implementation
    def _on_save_file(self, event=None):
        if self.text.cget('state') == 'disabled':
            tk.messagebox.showinfo('Encrypted Notepad', 'This file is opened as read-only.')
            return False
        if self.fpath == '': # If new file => Switch to Save As
            return self._on_save_file_as()
        if not self.text.edit_modified(): # If not modified => Return to window
            return False
        text = self.text.get('1.0', 'end-1c')

        if self.key1:

            # Encode text with key2
            try:
                text = Fernet(self.key2).encrypt(text.encode()).decode()
            except InvalidToken:
                tk.messagebox.showerror(title='Encrypted Notepad', message='Encryption failed. Could not save the file.\nTry "Save As..." with a new password.')
                return False

            # Encode key2 with key1
            # The header can be reused, but we want the header to rather change every time (Fernet is a probabilistic encryption)
            try:
                text += '====' + Fernet(self.key1).encrypt(self.key2).decode()
            except InvalidToken:
                tk.messagebox.showerror(title='Encrypted Notepad', message='Encryption failed. Could not save the file.\nTry "Save As..." with a new password.')
                return False

        try:
            file = open(self.fpath, 'w')
            file.write(text)
            file.close()
        except IOError:
            tk.messagebox.showerror(title='Encrypted Notepad', message='I/O error. Could not save the file.')
            return False
        else:
            file.close()
        self.text.edit_modified(False)
        self._on_change()
        return True


    # Read-only password implementation
    def _on_save_file_as(self, event=None):
        if self.text.cget('state') == 'disabled':
            tk.messagebox.showinfo('Encrypted Notepad', 'This file is opened as read-only.')
            return False
        fpath = tk.filedialog.asksaveasfilename(defaultextension='.txt')
        if fpath == '': # Cancel => Return to window
            return False
        fname = os.path.basename(fpath)

        while True:
            # PasswordDialog returns ('master password', boolean for read-only passworod, 'read-only password') on OK and None on Cancel
            diag = CreatePasswordDialog(self)
            if diag.result is not None and diag.result[1] and diag.result[2] != '' and diag.result[0] == '':
                tk.messagebox.showinfo('Encrypted Notepad', 'You cannot set a read-only password without setting a master password.')
            elif diag.result is not None and diag.result[1] and diag.result[2] != '' and diag.result[0] == diag.result[2]:
                tk.messagebox.showinfo('Encrypted Notepad', 'The master password cannot be the same as the read-only password.')
            else:
                break
        text = self.text.get('1.0', 'end-1c')
        if diag.result is None or diag.result[0] == '': # Cancel or OK with no master password => Save without encryption
            key1 = None
            key2 = None
        else: # OK with password(s) => Save with encryption

            # Encode text with the read-only password (the read-only password can be '')
            # If no read-only password is set, use a randomly generated key
            if diag.result[1]:
                try:
                    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=self.salt, iterations=self.iter, backend=default_backend())
                    key2 = base64.urlsafe_b64encode(kdf.derive(diag.result[2].encode())) # Can only use kdf once
                except ImportError:
                    tk.messagebox.showerror(title='Encrypted Notepad', message='Some dlls are missing. Use "--path=...bin" option in Pyinstaller to explicitly feed the dlls.')
                    return False
            else:
                key2 = Fernet.generate_key()
            try:
                text = Fernet(key2).encrypt(text.encode()).decode()
            except InvalidToken:
                tk.messagebox.showerror(title='Encrypted Notepad', message='Encryption failed. Could not save the file.')
                return False
            except ImportError:
                tk.messagebox.showerror(title='Encrypted Notepad', message='Some dlls are missing. Use "--path=...bin" option in Pyinstaller to explicitly feed the dlls.')
                return False

            # Encode key2 with the master password
            kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=self.salt, iterations=self.iter, backend=default_backend())
            key1 = base64.urlsafe_b64encode(kdf.derive(diag.result[0].encode())) # Can only use kdf once
            try:
                text += '====' + Fernet(key1).encrypt(key2).decode()
            except InvalidToken:
                tk.messagebox.showerror(title='Encrypted Notepad', message='Encryption failed. Could not save the file.')
                return False

        try:
            file = open(fpath, mode='w')
            file.write(text)
            file.close()
        except IOError:
            tk.messagebox.showerror(title='Encrypted Notepad', message='I/O error. Could not save the file.')
            return False
        else:
            file.close()
        self.fpath = fpath
        self.fname = fname
        self.key1 = key1
        self.key2 = key2
        self.text.edit_modified(False)
        self._on_change()
        self._update_recent_files(fpath)
        return True


    def _on_exit(self, event=None):
        if self.text.edit_modified():
            ans = tk.messagebox.askyesnocancel('Encrypted Notepad', 'Do you want to save changes to ' + self.fname + '?')
            if ans: # Yes
                if not self._on_save_file(): # If the user cancels saving, do not open a new text
                    return
            elif ans is None: # Cancel
                return
        if root.state() == 'normal':
            self.cp.set('settings', 'fullscreen', str(False))
            self.cp.set('settings', 'window', root.geometry())
        elif root.state() == 'zoomed':
            self.cp.set('settings', 'fullscreen', str(True))
        self.cp.set('settings', 'ignore_case', str(self.fr.ignorecase.get()))
        self.cp.set('settings', 'whole_word', str(self.fr.wholeword.get()))
        self.cp.set('settings', 'within_selection', str(self.fr.withinsel.get()))
        self.cp.set('settings', 'regular_expression', str(self.fr.regexp.get()))
        self.cp.write2()
        root.quit()

    def _on_undo(self, event=None):
        try:
            self.text.edit_undo()
            self.text.event_generate('<ButtonRelease-1>')
        except:
            pass

    def _on_redo(self, event=None):
        try:
            self.text.edit_redo()
            self.text.event_generate('<ButtonRelease-1>')
        except:
            pass

    # The event <<Cut>> itself does not trigger <<KeyRelease>>, so the status bar is not updated.
    # On the other hand, triggering <Control-x> generates key strokes that the user did not press.
    # So generate both <<Cut>> and <ButtonRelease-1> to solve these issues.
    def _on_cut(self, event=None):
        self.text.event_generate('<<Cut>>')
        self.text.event_generate('<ButtonRelease-1>')

    def _on_copy(self, event=None):
        self.text.event_generate('<<Copy>>')
        self.text.event_generate('<ButtonRelease-1>')

    def _on_paste(self, event=None):
        self.text.event_generate('<<Paste>>')
        self.text.event_generate('<ButtonRelease-1>')

    def _on_delete(self, event=None):
        self.text.event_generate('<<Clear>>')
        self.text.event_generate('<ButtonRelease-1>')

    def _on_select_all(self, event=None):
        self.text.event_generate('<<SelectAll>>')
        self.text.event_generate('<ButtonRelease-1>')

    def _on_find_replace(self, event=None):
        self.fr.deiconify()

    def _on_find_next(self, event=None):
        self.fr.find_next()

    def _on_find_previous(self, event=None):
        self.fr.find_previous()

    def _on_time_date(self, event=None):
        now = datetime.now().strftime('%I:%M %p %m/%d/%Y')
        if self.text.tag_ranges('sel'):
            if self.text.compare('sel.first', '<', 'sel.last'):
                start = self.text.index('sel.first')
            else:
                start = self.text.index('sel.last')
            self.text.replace('sel.first', 'sel.last', now) # replace selection
        else:
            start = self.text.index('insert') # get insert start position
            self.text.insert('insert', now) # insert
        self.text.tag_add('sel', start, 'insert') # select inserted string
        self.text.edit_separator()
        self.text.event_generate('<ButtonRelease-1>')

    def _on_random_string(self, event=None):
        chars = string.ascii_letters + string.punctuation + string.digits # candidate letters
        pwd = ''.join(choice(chars) for x in range(randint(20, 30))) # generate random password
        if self.text.tag_ranges('sel'):
            if self.text.compare('sel.first', '<', 'sel.last'):
                start = self.text.index('sel.first')
            else:
                start = self.text.index('sel.last')
            self.text.replace('sel.first', 'sel.last', pwd) # replace selection
        else:
            start = self.text.index('insert') # get insert start position
            self.text.insert('insert', pwd) # insert
        self.text.tag_add('sel', start, 'insert') # select inserted string
        self.text.edit_separator()
        self.text.event_generate('<ButtonRelease-1>')

    def _on_word_wrap(self, event=None):
        if self.wrap_type.get() == 0: # None
            self.text.config(wrap='none')
            self.hscroll.show()
        elif self.wrap_type.get() == 1: # Word Wrap
            self.text.config(wrap='word')
            self.hscroll.hide()
        else: # Character Wrap
            self.text.config(wrap='char')
            self.hscroll.hide()
        self.cp.set('settings', 'wrap_type', str(self.wrap_type.get()))

    def _on_font_color(self, event=None):
        f = font.nametofont(self.text.cget('font'))
        current_family = f.cget('family')
        current_size = f.cget('size')
        current_weight = f.cget('weight')
        current_slant = f.cget('slant')
        current_underline = f.cget('underline')
        current_overstrike = f.cget('overstrike')
        current_fg_color = self.text.cget('foreground')
        current_bg_color = self.text.cget('background')
        current_fg_hex = rgb16_to_hex(self.winfo_rgb(current_fg_color))
        current_bg_hex = rgb16_to_hex(self.winfo_rgb(current_bg_color))
        diag = self.FontColorDialog(self, fontobj=f, fgcolorhex=current_fg_hex, bgcolorhex=current_bg_hex)
        if diag.result is not None: # OK
            if diag.result > 0.5: # Bright => Make the cursor black
                self.text.config(insertbackground='black')
            else: # Bright => Make the cursor white
                self.text.config(insertbackground='white')
            # Update .ini
            self.cp.set('settings', 'font', f.cget('family'))
            self.cp.set('settings', 'size', str(f.cget('size')))
            self.cp.set('settings', 'bold', str(f.cget('weight')=='bold'))
            self.cp.set('settings', 'italic', str(f.cget('slant')=='italic'))
            self.cp.set('settings', 'underline', str(f.cget('underline')==1))
            self.cp.set('settings', 'strikeout', str(f.cget('overstrike')==1))
            self.cp.set('settings', 'text_color', self.text.cget('foreground'))
            self.cp.set('settings', 'background_color', self.text.cget('background'))
        else: # Cancel
            f.config(family=current_family, size=current_size, weight=current_weight, slant=current_slant, underline=current_underline, overstrike=current_overstrike)
            self.text.config(foreground=current_fg_color)
            self.text.config(background=current_bg_color)
            self.text.tag_configure('normal', background=current_bg_color)
        self.text.focus_set()

    def _on_statusbar(self, event=None):
        if self.status_on.get():
            self.status.show()
        else:
            self.status.hide()
        self.cp.set('settings', 'status_bar', str(self.status_on.get()))

    def _on_about(self, event=None):
        AboutDialog(self)
        self.text.focus_set()
        #tk.messagebox.showinfo(title='About Encrypted Notepad', message='This is Encrypted Notepad.')


    # The default font of Tkinter.Text is a named font 'TkFixedFont', which consists of the following attributes
    #  -family = 'Courier New'
    #  -size = 10
    #  -weight = 'normal'
    #  -slant = 'roman'
    #  -underline = 0
    #  -overstrike = 0
    # Class Arguments:
    #   fontobj : an instance of the tkinter.Font class (this is NOT the name of a named font)
    #   fgcolorhex : the hex string of a foreground (text) color
    #   bgcolorhex : the hex string of a background color
    # When pressed OK, the dialog returns the brightness of the background color in the scale of 0.0 - 1.0, so the parent
    # window can adjust the color of the cursor so it is visible.
    # When pressed Cancel, the dialog returns None, as is usual for the Dialog class.
    class FontColorDialog(Dialog):
        def __init__(self, parent, fontobj, fgcolorhex, bgcolorhex):
            self.font = fontobj
            self.font_list = list(set(font.families()))
            self.font_list.sort()
            self.size_list = ['8','9','10','11','12','14','16','18','20','22','24','26','28','36','48','72']
            self.font_list_var = tk.StringVar(value=self.font_list)
            self.size_list_var = tk.StringVar(value=self.size_list)

            self.size = tk.StringVar(value=str(self.font.cget('size')))
            self.bold = tk.BooleanVar(value=self.font.cget('weight') == 'bold')
            self.italic = tk.BooleanVar(value=self.font.cget('slant') == 'italic')
            self.underline = tk.BooleanVar(value=self.font.cget('underline') == 1)
            self.overstrike = tk.BooleanVar(value=self.font.cget('overstrike') == 1)
            self.fghex = fgcolorhex
            self.bghex = bgcolorhex

            Dialog.__init__(self, parent=parent, title='Font/Color')

        def body(self, parent):

            self.frame = tk.Frame(self, padx=15, pady=10)

            ## Font Pane
            ttk.Label(self.frame, text='Font:', anchor='w').grid(row=0, column=0, sticky='w')

            listframe = ttk.Frame(self.frame, borderwidth=2, relief='sunken')
            self.lb_family = tk.Listbox(listframe, listvariable=self.font_list_var, exportselection=False, bd=0, width=len(max(self.font_list, key=len)))
            sb_family = ttk.Scrollbar(listframe, orient='vertical')
            self.lb_family.config(yscrollcommand=sb_family.set)
            sb_family.config(command=self.lb_family.yview)
            self.lb_family.pack(side='left', fill='y')
            sb_family.pack(side='right', fill='y')
            x = self.font_list.index(self.font.cget('family'))
            self.lb_family.selection_set(x)
            self.lb_family.see(x)
            self.lb_family.activate(x)
            self.lb_family.selection_anchor(x)
            self.lb_family.bind('<<ListboxSelect>>', self.set_family)
            listframe.grid(row=1, column=0, rowspan=7, sticky='w')


            ## Size Pane
            ttk.Label(self.frame, text='Size:', anchor='w').grid(row=0, column=1, sticky='w', padx=20)
            sizeframe = ttk.Frame(self.frame, borderwidth=2, relief='sunken')
            self.en_size = tk.Entry(sizeframe, width=5, bd=0, relief='groove', textvariable=self.size, validate='key')
            self.en_size.configure(validatecommand=(self.en_size.register(self.validate_size), '%P', '%d')) # Only digits are allowed
            self.en_size.pack(side='top', fill='x')
            self.lb_size = tk.Listbox(sizeframe, listvariable=self.size_list_var, exportselection=False, bd=0, height=9, width=5)
            sb_size = ttk.Scrollbar(sizeframe, orient='vertical')
            self.lb_size.config(yscrollcommand=sb_size.set)
            sb_size.config(command=self.lb_size.yview)
            self.lb_size.pack(side='left', fill='y')
            sb_size.pack(side='right', fill='y')

            self.en_size.bind('<Return>', self.set_size)
            self.lb_size.bind('<<ListboxSelect>>', self.select_size)

            sizeframe.grid(row=1, column=1, rowspan=7, padx=20)


            # Style/Color Pane
            ttk.Label(self.frame, text='Style:', anchor='w').grid(row=0, column=2, columnspan=2, sticky='w')
            ttk.Checkbutton(self.frame, text='Bold', variable=self.bold, command=self.set_bold).grid(row=1, column=2, columnspan=2, sticky='w')
            ttk.Checkbutton(self.frame, text='Italic', variable=self.italic, command=self.set_italic).grid(row=2, column=2, columnspan=2, sticky='w')
            ttk.Checkbutton(self.frame, text='Underline', variable=self.underline, command=self.set_underline).grid(row=3, column=2, columnspan=2, sticky='w')
            ttk.Checkbutton(self.frame, text='Strikeout', variable=self.overstrike, command=self.set_overstrike).grid(row=4, column=2, columnspan=2, sticky='w')

            ttk.Label(self.frame, text='Color:', anchor='w').grid(row=5, column=2, columnspan=2, sticky='w', pady=(10,0))
            ttk.Label(self.frame, text='Text:', anchor='w').grid(row=6, column=2, sticky='w')
            ttk.Label(self.frame, text='Background:', anchor='w').grid(row=7, column=2, sticky='w', padx=(0,6))

            smallfont = font.Font(size=7)
            self.tclabel = ttk.Label(self.frame, background=self.fghex, relief='sunken', font=smallfont, width=4)
            self.tclabel.grid(row=6, column=3, sticky='w', pady=2)
            self.tclabel.bind('<Button-1>', self.set_fg_color)
            self.bclabel = ttk.Label(self.frame, background=self.bghex, relief='sunken', font=smallfont, width=4)
            self.bclabel.grid(row=7, column=3, sticky='w', pady=2)
            self.bclabel.bind('<Button-1>', self.set_bg_color)

            self.frame.pack()
            self.iconbitmap(resource_path('security.ico'))
            self.set_size()

        def apply(self, event=None):
            self.result = hex_to_brightness(self.bghex)

        def set_family(self, event=None):
            self.font.config(family=self.font_list[self.lb_family.curselection()[0]])

        def validate_size(self, tobeinserted, actiontype):
            if actiontype == '1' and not tobeinserted.isdigit(): # Action is 'insert' and to-be-inserted is non-digit
                return False
            return True

        def set_size(self, event=None):
            size = self.size.get()
            self.font.configure(size=int(size))
            self.lb_size.selection_clear(0, 'end') # Clear the list selection
            try: # Choose the matching list item if any
                index = self.size_list.index(size) # If not match, throws ValueError
                self.lb_size.selection_set(index)
                self.lb_size.see(index)
                self.lb_size.activate(index)
                self.lb_size.selection_anchor(index)
            except ValueError:
                pass

        def select_size(self, event=None):
            # Retrieve the list item and overwrite Entry
            index = self.lb_size.curselection()
            if index: # <<ListboxSelect>> Event is triggered by selecting the text in en_size Entry, in which case index == ()
                size = self.lb_size.get(index)
                self.en_size.delete(0, 'end')
                self.en_size.insert(0, size)
                self.font.configure(size=int(size))

        def set_bold(self):
            self.font.configure(weight='bold' if self.bold.get() else 'normal')

        def set_italic(self):
            self.font.configure(slant='italic' if self.italic.get() else 'roman')

        def set_underline(self):
            self.font.configure(underline=self.underline.get())

        def set_overstrike(self):
            self.font.configure(overstrike=self.overstrike.get())

        def set_fg_color(self, event=None):
            # Need to supply a hex color into initial color
            # If you supply RGB to it, it will convert it to a hex assuming that each R, G, or B is small int (max 255)
            # So if it is actually a normal int (max 65535), it will give an error on invalid color...
            (rgb, hx) = colorchooser.askcolor(parent=self, title='Choose Text Color', initialcolor=self.fghex)
            if hx is not None:
                self.fghex = hx
                self.tclabel.config(background=hx)
                self.parent.text.configure(foreground=hx)

        def set_bg_color(self, event=None):
            (rgb, hx) = colorchooser.askcolor(parent=self, title='Choose Background Color', initialcolor=self.bghex)
            if hx is not None:
                self.bghex = hx
                self.bclabel.config(background=hx)
                self.parent.text.configure(background=hx)
                self.parent.text.tag_configure('normal', background=hx)


    class FindReplace(tk.Toplevel):
        def __init__(self, parent, ignorecase=True, wholeword=False, withinsel=False, regexp=False):
            tk.Toplevel.__init__(self, master=parent)
            self.title('Find/Replace')

            self.ignorecase = tk.BooleanVar()
            self.wholeword = tk.BooleanVar()
            self.withinsel = tk.BooleanVar()
            self.regexp = tk.BooleanVar()
            self.ignorecase.set(ignorecase)
            self.wholeword.set(wholeword)
            self.withinsel.set(withinsel)
            self.regexp.set(regexp)

            self.strfind = tk.StringVar()
            self.strreplace = tk.StringVar()

            self.strfind_list = []
            self.strreplace_list = []

            self.frame_entry = ttk.Frame(self)
            self.frame_buttons = ttk.Frame(self)
            self.frame_entry.pack(side='left', fill='x', expand=True, anchor='nw', padx=15, pady=10)
            self.frame_buttons.pack(side='right', anchor='ne', padx=15, pady=10)
            self.frame_entry.grid_columnconfigure(1, weight=1)

            ttk.Label(self.frame_entry, text='Search for:', anchor='w').grid(row=0, column=0, sticky='w')
            self.entry_find = ttk.Combobox(self.frame_entry, textvariable=self.strfind)
            self.entry_find.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0,20))

            ttk.Label(self.frame_entry, text='Replace with:', anchor='w').grid(row=2, column=0, sticky='w')
            self.entry_repl = ttk.Combobox(self.frame_entry, textvariable=self.strreplace)
            self.entry_repl.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(0,20))

            ttk.Checkbutton(self.frame_entry, text='Ignore Case', variable=self.ignorecase).grid(row=4, column=0, sticky='w')
            ttk.Checkbutton(self.frame_entry, text='Whole Word', variable=self.wholeword).grid(row=5, column=0, sticky='w')
            ttk.Checkbutton(self.frame_entry, text='Within Selection', variable=self.withinsel).grid(row=6, column=0, sticky='w')
            ttk.Checkbutton(self.frame_entry, text='Regular Expression', variable=self.regexp).grid(row=7, column=0, sticky='w')
            style = ttk.Style(self.frame_entry)
            f = font.Font(**font.nametofont(style.lookup('Label', 'font')).configure())
            f.configure(underline=1)
            style.configure('Underline.Label', foreground='blue', font=f)
            self.link_regexp = ttk.Label(self.frame_entry, text='(Python regex)', style='Underline.Label')
            self.link_regexp.grid(row=7, column=1, sticky='w')
            self.link_regexp.bind('<Button-1>', lambda event: webbrowser.open_new('https://pypi.org/project/regex/'))

            ttk.Button(self.frame_buttons, text='Find Next', command=self.find_next).pack(fill='x', pady=2)
            ttk.Button(self.frame_buttons, text='Find Previous', command=self.find_previous).pack(fill='x', pady=2)
            ttk.Button(self.frame_buttons, text='Find All', command=self.find_all).pack(fill='x', pady=2)

            ttk.Separator(self.frame_buttons, orient='horizontal').pack(fill='x', pady=6)

            ttk.Button(self.frame_buttons, text='Replace and Next', command=self.replace_next).pack(fill='x', pady=2)
            ttk.Button(self.frame_buttons, text='Replace and Prev.', command=self.replace_previous).pack(fill='x', pady=(2,4))
            ttk.Button(self.frame_buttons, text='Replace All', command=self.replace_all).pack(fill='x', pady=2)

            ttk.Button(self.frame_buttons, text='Close', command=self.close).pack(fill='x', pady=(20,0))
            self.protocol('WM_DELETE_WINDOW', self.close)

            self.entry_find.bind('<Return>', self.find_next)
            self.entry_repl.bind('<Return>', self.replace_next)
            # https://stackoverflow.com/questions/53848622/how-to-bind-keypress-event-for-combobox-drop-out-menu-in-tkinter-python-3-7
            # https://stackoverflow.com/questions/59763822/show-combobox-drop-down-while-editing-text-using-tkinter
            self.entry_find_internal_listbox_name = self.entry_find.tk.call('ttk::combobox::PopdownWindow', self.entry_find) + '.f.l'
            self.entry_repl_internal_listbox_name = self.entry_repl.tk.call('ttk::combobox::PopdownWindow', self.entry_repl) + '.f.l'
            self.entry_find._bind(('bind', self.entry_find_internal_listbox_name), '<Delete>', self.delete_find, None)
            self.entry_repl._bind(('bind', self.entry_repl_internal_listbox_name), '<Delete>', self.delete_repl, None)
            self.bind('<Escape>', self.close)
            self.bind('<FocusOut>', lambda event: self.master.text.tag_remove('match', '1.0', 'end'))
            self.bind('<FocusIn>', self.focusin)
            self.bind('<Expose>', self.exposed)
            self.bind('<F3>', self.find_next)
            self.bind('<Shift-F3>', self.find_previous)

            self.iconbitmap(resource_path('security.ico'))
            self.wm_geometry("450x270")
            self.entry_find.focus_set()

        # Get the minimum tag among 'insert', 'sel.first', and 'sel.last'
        # It assumes that 'insert' is equal to one of 'sel.first' and 'sel.last', if at all
        def _min_index(self):
            if self.master.text.tag_ranges('sel'):
                if self.master.text.compare('sel.first', '<', 'sel.last'):
                    return 'sel.first'
                else:
                    return 'sel.last'
            else:
                return 'insert'

        # Get the maximum tag among 'insert', 'sel.first', and 'sel.last'
        # It assumes that 'insert' is equal to one of 'sel.first' and 'sel.last', if at all
        def _max_index(self):
            if self.master.text.tag_ranges('sel'):
                if self.master.text.compare('sel.first', '<', 'sel.last'):
                    return 'sel.last'
                else:
                    return 'sel.first'
            else:
                return 'insert'

        def _get_pattern(self, backwards):
            str = self.strfind.get()
            if str == '':
                return None

            # Update recent keywords
            str = self.strfind.get()
            if str in self.strfind_list:
                self.strfind_list.remove(str)
            self.strfind_list.insert(0, str)
            if len(self.strfind_list) > 5:
                self.strfind_list.pop(-1)
            self.entry_find.config(values=self.strfind_list)

            if not self.regexp.get():
                str = re.escape(str)
            # Known issue:
            # If the text is 'wordword' and the cursor is like 'word|word' and you search for the whole word of 'word',
            # the current algorithm catches the second (find next) or the first (find previous).
            if self.wholeword.get():
                str = r'\b' + str + r'\b'
            if backwards:
                str = '(?r)' + str
            return str

        def delete_find(self, event=None):
            index = self.entry_find.tk.call(self.entry_find_internal_listbox_name, 'curselection')
            if index:
                self.strfind_list.pop(index[0])
                self.entry_find.event_generate('<Escape>')
                self.entry_find.config(values=self.strfind_list)
                self.entry_find.after(1, lambda: self.entry_find.event_generate('<Button-1>'))

        def delete_repl(self, event=None):
            index = self.entry_repl.tk.call(self.entry_repl_internal_listbox_name, 'curselection')
            if index:
                self.strreplace_list.pop(index[0])
                self.entry_repl.event_generate('<Escape>')
                self.entry_repl.config(values=self.strreplace_list)
                self.entry_repl.after(1, lambda: self.entry_repl.event_generate('<Button-1>'))

        def _find_within(self, str, left, right):
            left = self.master.text.index(left) # If left is specified as 'sel.first', we need to convert it to 'l.c' form.
            try:
                if self.ignorecase.get():
                    match = re.search(str, self.master.text.get(left, right), re.MULTILINE|re.IGNORECASE)
                else:
                    match = re.search(str, self.master.text.get(left, right), re.MULTILINE)
            except re.error:
                tk.messagebox.showerror(title='Encrypted Notepad', message='Pattern syntax error.')
                return None
            except RecursionError:
                tk.messagebox.showerror(title='Encrypted Notepad', message='Too many recursion.')
                return None
            except:
                tk.messagebox.showerror(title='Encrypted Notepad', message='Search failed.')
                return None
            if match:
                # Remove tags
                self.master.text.tag_remove('sel', '1.0', 'end')
                self.master.text.tag_remove('match', '1.0', 'end')
                self.master.text.tag_remove('find all', '1.0', 'end')
                self.master.status.misc.configure(text='')
                # Set new tags
                start_index = '%s+%dc' % (left, match.start())
                end_index = '%s+%dc' % (left, match.end())
                self.master.text.tag_add('match', start_index, end_index)
                self.master.text.tag_add('sel', start_index, end_index)
                self.master.text.mark_set('insert', end_index)
                self.master._on_change()
                self.master.text.see('insert')
                return True
            else:
                return False

        def find_next(self, event=None):
            str = self._get_pattern(backwards=False)
            if str is None:
                return
            if self.withinsel.get():
                if not self.master.text.tag_ranges('sel'):
                    return
                if self.master.text.compare('sel.first', '<', 'sel.last'):
                    left = 'sel.first'
                    right = 'sel.last'
                else:
                    left = 'sel.last'
                    right = 'sel.first'
            else:
                left = self._max_index()
                right = 'end-1c'

            res = self._find_within(str, left, right)
            if res is None:
                return
            if res is False and not self.withinsel.get():
                res = self._find_within(str, '1.0', 'end-1c')
            if res is False:
                tk.messagebox.showinfo(title='Encrypted Notepad', message='Not found.')

        def find_previous(self, event=None):
            str = self._get_pattern(backwards=True)
            if str is None:
                return
            if self.withinsel.get():
                if not self.master.text.tag_ranges('sel'):
                    return
                if self.master.text.compare('sel.first', '<', 'sel.last'):
                    left = 'sel.first'
                    right = 'sel.last'
                else:
                    left = 'sel.last'
                    right = 'sel.first'
            else:
                left = '1.0'
                right = self._min_index()

            res = self._find_within(str, left, right)
            if res is None:
                return
            if res is False and not self.withinsel.get():
                res = self._find_within(str, '1.0', 'end-1c')
            if res is False:
                tk.messagebox.showinfo(title='Encrypted Notepad', message='Not found.')

        def find_all(self):
            self.master.text.tag_remove('match', '1.0', 'end')
            self.master.text.tag_remove('find all', '1.0', 'end')
            self.master.status.misc.configure(text='')
            str = self._get_pattern(backwards=False)
            if str is None:
                return
            if self.ignorecase.get():
                p = re.compile(str, re.MULTILINE|re.IGNORECASE)
            else:
                p = re.compile(str, re.MULTILINE)
            if self.withinsel.get():
                if self.master.text.tag_ranges('sel'):
                    start = 'sel.first'
                    end = 'sel.last'
                    left = self.master.text.index('sel.first' if self.master.text.compare('sel.first', '<', 'sel.last') else 'sel.last')
                else:
                    return
            else:
                start = '1.0'
                end = 'end-1c'
                left = '1.0'

            count = 0
            for match in p.finditer(self.master.text.get(start, end)):
                self.master.text.tag_add('find all', left + '+%dc' % match.start(), left + '+%dc' % match.end())
                count += 1
            counttext = ('%d occurrence' % count) + ('s' if count > 1 else '') + ' found'
            self.master.status.misc.configure(text=counttext)
            tk.messagebox.showinfo(title='Encrypted Notepad', message=counttext)

        def _replace_fullmatch(self):
            # Remove tags
            self.master.text.tag_remove('match', '1.0', 'end')
            self.master.text.tag_remove('find all', '1.0', 'end')
            self.master.status.misc.configure(text='')
            # Get pattern
            str = self._get_pattern(backwards=False)
            if str is None:
                return
            if self.ignorecase.get():
                p = re.compile(str, re.MULTILINE|re.IGNORECASE)
            else:
                p = re.compile(str, re.MULTILINE)

            # Update recent replacement keywords
            str2 = self.strreplace.get()
            if str2 in self.strreplace_list:
                self.strreplace_list.remove(str2)
            self.strreplace_list.insert(0, str2)
            if len(self.strreplace_list) > 5:
                self.strreplace_list.pop(-1)
            self.entry_repl.config(values=self.strreplace_list)

            # If selection matches the pattern, replace
            if self.master.text.tag_ranges('sel') and p.fullmatch(self.master.text.get('sel.first', 'sel.last')):
                rpl = p.sub(str2, self.master.text.get('sel.first', 'sel.last'))
                self.master.text.replace('sel.first', 'sel.last', rpl)
                self.master.text.edit_separator()


        # If the selected text is not the 'found' text that matches the search keyword, then invoke 'find next' instead
        def replace_next(self, event=None):
            self._replace_fullmatch()
            return self.find_next()

        # If the selected text is not the 'found' text that matches the search keyword, then invoke 'find previous' instead
        def replace_previous(self):
            self._replace_fullmatch()
            return self.find_previous()

        def replace_all(self):
            self.master.text.tag_remove('match', '1.0', 'end')
            self.master.text.tag_remove('find all', '1.0', 'end')
            self.master.status.misc.configure(text='')
            p = self._get_pattern(backwards=False)
            if p is None:
                return
            if self.withinsel.get():
                if self.master.text.tag_ranges('sel'):
                    start = 'sel.first'
                    end = 'sel.last'
                    left = self.master.text.index('sel.first' if self.master.text.compare('sel.first', '<', 'sel.last') else 'sel.last')
                else:
                    return
            else:
                start = '1.0'
                end = 'end-1c'

            text, count = p.subn(self.strreplace.get(), self.master.text.get(start, end))
            self.master.text.replace(start, end, text)
            self.master.text.edit_separator()
            if self.withinsel.get():
                self.master.text.tag_add('match', left, 'insert')
                self.master.text.tag_add('sel', left, 'insert')
            counttext = ('%d occurrence' % count) + ('s' if count > 1 else '') + ' replaced'
            self.master.status.misc.configure(text=counttext)
            tk.messagebox.showinfo(title='Encrypted Notepad', message=counttext)

        def focusin(self, event=None):
            if self.master.text.tag_ranges('sel'):
                self.master.text.tag_add('match', 'sel.first', 'sel.last')

        def exposed(self, event=None):
            self.entry_find.focus_set()

        def close(self, event=None):
            # clear tags
            self.master.text.tag_remove('match', '1.0', 'end')
            self.master.text.tag_remove('find all', '1.0', 'end')
            self.master.status.misc.configure(text='')
            self.withdraw()


class EnterPasswordDialog(Dialog):
    def __init__(self, parent, fname):
        self.pwd = tk.StringVar()
        self.fname = fname
        Dialog.__init__(self, parent=parent, title='Enter Password')

    def body(self, parent):
        smallfont = font.Font(size=7)
        self.frame = tk.Frame(self, padx=15, pady=7) # ttk.Frame does not allow padx, pady
        ttk.Label(self.frame, text='Enter the password for ' + self.fname, anchor='w').grid(row=1, column=0, columnspan=2, sticky='w')
        self.entry_pwd = ttk.Entry(self.frame, textvariable=self.pwd, show='*')
        self.entry_pwd.grid(row=2, column=0, sticky='w', pady=(0,10))
        self.button_pwd = tk.Button(self.frame, text='***', font=smallfont, height=1, width=3, relief='groove', command=self.toggle_pwd)
        self.button_pwd.grid(row=2, column=1, sticky='w', padx=(10,0), pady=(0,10))
        tk.Button(self.frame, text='\N{KEYBOARD}', height=1, width=3, relief='groove', command=self.onscreenkeyboard).grid(row=2, column=2, padx=(10,0), pady=(0,10))
        self.iconbitmap(resource_path('security.ico'))
        self.frame.pack()
        self.entry_pwd.focus_set()

    def apply(self):
        self.result = self.pwd.get()

    def onscreenkeyboard(self):
        if platform.system() == 'Windows':
            subprocess.Popen(['osk'], shell=True)
        elif platform.system() == 'Darwin': # Mac
            os.system('open -a KeyboardViewer')
        elif platform.system() == 'Linux': # Ubuntu
            subprocess.Popen(['onboard', ])
        else:
            tk.messagebox.showinfo(title='Encrypted Notepad', message='On-Screen Keyboard is not available.')

    def toggle_pwd(self):
        if self.entry_pwd['show'] == '*':
            self.entry_pwd.configure(show='')
            self.button_pwd.configure(text='\N{EYE}')
        else:
            self.entry_pwd.configure(show='*')
            self.button_pwd.configure(text='***')



# '=' is a padding for Base64 URL-safe encoding, so it won't repeat for 4 times.
# So '====' can be used as a separator.
class CreatePasswordDialog(Dialog):
    def __init__(self, parent):
        # Dialog calls body() in __init__() so we need to define attributes before that
        self.pwd = tk.StringVar()
        self.read_check = tk.BooleanVar()
        self.read_pwd = tk.StringVar()
        Dialog.__init__(self, parent=parent, title='Set Password')

    def body(self, parent):
        smallfont = font.Font(size=7)
        self.frame = tk.Frame(self, padx=15, pady=7)
        ttk.Label(self.frame, text='Master Password:', anchor='w').grid(row=1, column=0, columnspan=2, sticky='w')
        self.entry_pwd = ttk.Entry(self.frame, textvariable=self.pwd, show='*')
        self.entry_pwd.grid(row=2, column=0, sticky='w', pady=(0,10))
        self.button_pwd = tk.Button(self.frame, text='***', font=smallfont, height=1, width=3, relief='groove', command=self.toggle_pwd)
        self.button_pwd.grid(row=2, column=1, sticky='w', padx=(10,0), pady=(0,10))
        tk.Button(self.frame, text='\N{KEYBOARD}', height=1, width=3, relief='groove', command=self.onscreenkeyboard).grid(row=2, column=2, padx=(10,0), pady=(0,10))
        ttk.Checkbutton(self.frame, text='Read-Only Password:', variable=self.read_check, command=self.toggle_check).grid(row=3, column=0, columnspan=2, sticky='w')
        self.entry_read = ttk.Entry(self.frame, textvariable=self.read_pwd, show='*', state='disabled')
        self.entry_read.grid(row=4, column=0, sticky='w')
        self.button_read = tk.Button(self.frame, text='***', font=smallfont, height=1, width=3, relief='groove', command=self.toggle_read, state='disabled')
        self.button_read.grid(row=4, column=1, sticky='w', padx=(10,0))
        self.iconbitmap(resource_path('security.ico'))
        self.frame.pack()
        self.entry_pwd.focus_set()

    def apply(self):
        self.result = (self.pwd.get(), self.read_check.get(), self.read_pwd.get())

    def onscreenkeyboard(self):
        if platform.system() == 'Windows':
            subprocess.Popen(['osk'], shell=True)
        elif platform.system() == 'Darwin': # Mac
            os.system('open -a KeyboardViewer')
        elif platform.system() == 'Linux': # Ubuntu
            subprocess.Popen(['onboard', ])
        else:
            tk.messagebox.showinfo(title='Encrypted Notepad', message='On-Screen Keyboard is not available.')

    def toggle_check(self):
        if self.read_check.get():
            self.entry_read['state'] = 'enabled'
            self.button_read['state'] = 'normal'
        else:
            self.entry_read.configure(show='*')
            self.button_read.configure(text='***')
            self.entry_read['state'] = 'disabled'
            self.button_read['state'] = 'disabled'

    def toggle_pwd(self):
        if self.entry_pwd['show'] == '*':
            self.entry_pwd.configure(show='')
            self.button_pwd.configure(text='\N{EYE}')
        else:
            self.entry_pwd.configure(show='*')
            self.button_pwd.configure(text='***')

    def toggle_read(self):
        if self.entry_read['show'] == '*':
            self.entry_read.configure(show='')
            self.button_read.configure(text='\N{EYE}')
        else:
            self.entry_read.configure(show='*')
            self.button_read.configure(text='***')




class AboutDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent=parent, title='About Encrypted Notepad')

    def body(self, parent):
        frame = tk.Frame(self, padx=20, pady=20)
        tframe = tk.Frame(frame, bd=4, relief='sunken')
        tframe.pack(fill='both', expand=True)
        text = tk.Text(tframe, bg=tframe.cget('background'), bd=0)
        vscroll = ttk.Scrollbar(tframe, orient='vertical')
        text.grid(row=0, column=0, sticky='nesw')
        vscroll.grid(row=0, column=1, sticky='ns')
        tframe.grid_columnconfigure(0, weight=1)
        vscroll.config(command=text.yview)
        text.configure(yscrollcommand=vscroll.set)
        text.insert('1.0', r'''
Encrypted Notepad

Copyright (c) 2020 by Tetsuya Kaji

This software is licensed by the MIT license.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Except as contained in this notice, the name(s) of the above copyright holders
shall not be used in advertising or otherwise to promote the sale, use or
other dealings in this Software without prior written authorization.

Icon made by Freepik from www.flaticon.com

------------------------------------------------------------------------------

[Overview]

This program is a text editor with a feature to save/open a text file with Fernet encryption, intended to facilitate password management. A recommended use is:

1. Enter however many password information in the editor. E.g.,
	Facebook
	Username: xxyyzz
	Password: ******

2. Save the file with encryption with a master password. The created text file shows a random string when opened with other text editors. When you open the file with this program, you are asked to enter the master password, and you can view the original text.

3. You can even upload the file to a cloud (like Dropbox), so your password information won't be lost when your computer crashes.

4. When you need to create a new password for something, open the file and generate a random string (Edit > Insert Random String, or press F6). This way, having one password leaked does not make your other accounts vulnerable.

5. You can also set a read-only password. When you simply need to retrieve passwords from this file (and not to put in new ones), you don't have to worry about accidentally typing and deleting something. (You can still copy the contents in the read-only mode.)


[Notes]

 - When you go File > Save As..., you are asked to create a (master) password. You also have an option to create a read-only password along with a master password.

 - If a master password is empty, the file will not be encrypted.

 - A read-only password can only be set if the master password is not empty.

 - If the read-only password checkbox is on but the box is empty, anyone can open and see the file if they have your binary of this text editor.

 - The master password and the read-only password cannot be identical. When opening the file, the program automatically distinguishes the password and opens in a corresponding mode.

 - Settings are stored in enotepad.ini in the same folder as the program. If you want to restore all default settings, delete the ini file and restart the program.

 - Recent files are stored under File Menu up to 5. To delete all, click Clear Recent Files. You can also delete a specific item by editing the ini file.

 - The editor supports UTF-8 characters, while the encrypted file will only have URL-safe (hence ASCII-safe) characters.

 - In general, a password is recommended to be long rather than complicated (https://en.wikipedia.org/wiki/Password_strength).


[Algorithm]

 - Encryption key is generated by the user's password and the program's password ('salt').

 - If you modify the salt in the source code, the files encrypted by that binary cannot be opened by other binaries even if they know your password (and vice versa).

 - The read-only password is implemented as follows.

  1. The encryption key for the text file is generated with the read-only password and salt. If no read-only password is entered, a random key is generated.

  2. The above encryption key is encrypted with the master password and salt.


[Find/Replace]

 - This program supports find/replace based on the regular expressions through Python's regex module (https://pypi.org/project/regex/).

 - 'Whole Word' functionality is implemented through the regular expression.

 - A known glitch with 'Whole Word' is that, if there is a line with 'wordword' and the cursor is in the middle (word|word), Find Next and Find Previous on 'word' will catch each side of word, since the cursor itself is regarded as the boundary of a word.

 - Recent keywords are stored up to 5. You can delete them by pressing Delete while the keyword is selected in the dropdown list.
        ''')
        text.configure(state='disabled', wrap='word')
        self.iconbitmap(resource_path('security.ico'))
        frame.pack(side='top', fill='both', expand=True)

    def buttonbox(self):
        """Overrides Dialog.buttonbox() to suppress the Cancel button. """
        box = ttk.Frame(self)
        tk.Button(box, text="OK", width=10, command=self.ok, default='active').pack(side='left', padx=5, pady=5)
        self.bind("<Return>", self.ok)
        box.pack()




# https://stackoverflow.com/questions/51060894/adding-a-data-file-in-pyinstaller-using-the-onefile-option
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

if __name__ == '__main__':
    cwd = os.getcwd()
    root = tk.Tk()
    cp = ConfigParser2()
    cp.read(os.path.join(cwd, 'enotepad.ini'))
    root.iconbitmap(resource_path('security.ico'))

    root.geometry(cp.get2('settings', 'window', '400x300'))
    root.state('zoomed' if cp.getboolean2('settings', 'fullscreen', False) else 'normal')

    note = Notepad(root, cp=cp, salt=b'}\xc9\xf7\x10m\xc4g\xdb\xa7UL\xa8X\x98\x0f\xe6\xedv65\x9eRm\x00)\x1e\xeb\x08\xc9\x1f', iterations=100001)
    root.bind('<Escape>', lambda event: root.wm_state('iconic'))
    root.protocol('WM_DELETE_WINDOW', note._on_exit)
    note.pack(fill='both', expand=True);
    note.text.focus_set()

    root.mainloop()
