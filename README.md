# Encrypted_Notepad
A notepad with Fernet encryption/decryption (and flexible regex searches)

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

[How to Install]

For Windows, download enotepad.exe. For other OS, download Encrypted_Notepad.py and compile it.


[How to Uninstall]

Delete enotepad.exe and enotepad.ini.


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

 - The cursor itself is regarded as the boundary of a word in the 'Whole Word' option. So if there is a line with 'wordword' and the cursor is in the middle (word|word), Find Next and Find Previous on 'word' will catch each side of the word.

 - Recent keywords are stored up to 5. You can delete them by pressing Delete while the keyword is selected in the dropdown list.
