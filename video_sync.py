#! /usr/bin/python

import os
import json
import re
import unicodedata
import shutil
import codecs
from pprint import pprint
import hashlib
from datetime import datetime
from datetime import timedelta
import subprocess
import copy
import shlex

base = '/share/Video'  # Root dir of videos
popcorn_base = '/mnt/A410'
root_level = os.listdir(base)


#### Cannot us that for now
# def latest_update(root_level):
#     for level1 in root_level:  # loop years
#         #Only take folders that are assimilated to years, ex: 1999
#         if (re.match(r'^[0-9]{4}$', level1) and os.path.isdir('/'.join([base, level1]))):  # condition level1
#             #structure[level1] = {}
#             for level2 in os.listdir('/'.join([base, level1]).decode('latin-1')):
#                 if os.path.isdir('/'.join([base, level1, level2])):  # condition level2
#                     cur_path = '/'.join([base, level1, level2])
#                     if(datetime.fromtimestamp(os.path.getmtime(cur_path)) > datetime.now() - timedelta(hours=24)):
#                         pass #Next is making everything


#Function that reads the structure of the dirs of the videos
#Input: Base dirs as lit
#Output: Dict of dir structure of videos
def create_structure(base_level):
    structure = {} #Create empty structure
    #structure_with_date = {}
    for level1 in base_level:  # loop years. Level1 are years
        #Only take folders that are assimilated to years, ex: 1999
        if (re.match(r'^[0-9]{4}$', level1) and os.path.isdir('/'.join([base, level1]))):  # condition level1
            if(level1 == '0001' or level1 == '2008'):
                continue
            #structure[level1] = {}
            for level2 in os.listdir('/'.join([base, level1]).decode('utf-8')):
                '''loop level2. Level2 are folder with videos in them.
                The name of the folder is the name of the future concatenated video
                '''
                if os.path.isdir('/'.join([base, level1, level2])):  # If is dir
                    current_path = u'/'.join([base, level1, level2])  # Use folder as reference
                    ID,chapters_duration = create_folder_profile(current_path) #ID of the folder
                    structure[ID] = {}  # Empty dict
                    structure[ID]['path'] = current_path  #Fill path
                    structure[ID]['chapters_duration'] = chapters_duration
    return (structure)

#Function that takes a folder and returns a unique ID to identify a specific content of folder.
#Input: path to folder as string
#Output: ID as string
def create_folder_profile(folder):
    folder_profile = ''
    folder_list = {}
    chapters_duration = {}
    for filename in os.listdir(folder):  # loop files
        if os.path.isfile(u'/'.join([folder, filename])) and check_if_vid(filename):  # condition files
            cur_path = u'/'.join([folder, filename])
            chapters_duration[os.path.splitext(filename)[0]] = get_video_duration(cur_path)
            folder_list[filename] = md5_for_file(cur_path)
    for filename in sorted(folder_list.keys()):
        folder_profile += folder_list[filename]
        folder_profile += str(os.path.getsize(cur_path))
    return(folder_profile, chapters_duration)
def convert_folder(folder, ext):
    temp_folders = os.listdir(folder)
    for filename in os.listdir(folder):  # loop files
        if os.path.isfile(u'/'.join([folder, filename])) and check_if_vid(filename):  # condition files
            cur_path = u''.join([folder, filename])
            print(cur_path)
            execute_command("/share/Scripts/ffmpeg-static/ffmpeg -i '{}' -codec copy '{}'".format(cur_path, cur_path.rstrip(ext) + "_remake.mpg"))
    for filename in temp_folders:  # loop files
        if os.path.isfile(u'/'.join([folder, filename])) and check_if_vid(filename):  # condition files
            cur_path = u''.join([folder, filename])
            execute_command("mv '{}' '{}'".format(cur_path, cur_path.rstrip(ext) + ".NOT"))


def execute_command(command):
    proc = subprocess.Popen(command, shell=True)
    proc.wait()

#Function that takes a file and returns duration plus offset duration
#Input: filepath
#Outpu: timestamp
def get_video_duration(filepath):
    duration = re.compile('[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{2}')
    offset = re.compile('[0-9]{1}\.[0-9]{6}')
    filepath = filepath.encode('utf-8')
    command = "/share/Scripts/ffmpeg-static/ffprobe '{}'".format(filepath)
    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr = subprocess.PIPE)
    stdout, err = proc.communicate()
    vid_duration = re.findall(duration, err)[0]
    vid_offset = float(re.findall(offset, err)[0])
    total_duration = datetime.strptime(vid_duration, '%H:%M:%S.%f') + timedelta(seconds = vid_offset)
    #print vid_duration,vid_offset,type(vid_duration),type(vid_offset)
    return(total_duration.strftime('%H:%M:%S.%f'),str(vid_offset))


#Function that takes a file and gives back a hash of the first 10 block of file
#Input: File
#Output: Hash of 10 blocks of 128 bits of size
def md5_for_file(filepath, block_size=128):
    with open(filepath, 'r') as f:
        n = 1
        md5 = hashlib.md5()
        while True:
            data = f.read(block_size)
            n += 1
            if (n == 15):
                break
            md5.update(data)
    return (md5.hexdigest())



#Function that writes a dir structure to dir_tree.txt file
#Input: structure
#Output: NA
def write_structure(structure, file='dir_tree.txt'):
    with open(file, 'w') as outfile:
        json.dump(structure, outfile)
#Function that reads a dir file from a json file
#Input: dir_tree.txt file
#Output: structure dict
def read_structure_from_file(infile):
    with codecs.open(infile, 'r', 'utf-8') as f:
        try:
            structure = json.load(f)
        except:
            return {}
    return structure

#Function to change color of ouptut for readability
#Input: string to color and the color wished
#Output: colored string
def color(string, color):
    if color == 'red':
        return "\033[31m" + string + "\033[0m"
    elif color == 'green':
        return "\033[32m" + string + "\033[0m"
    elif color == 'bold':
        return "\033[1m"  + string + "\033[0m"
    elif color == 'yellow':
        return "\033[33m" + string + "\033[0m"


#Function that compares two dir structures and give our the differences
#Input: two structure, present and past
#Output:
def update_structure(past_structure, new_structure):
    new_paths = get_path_list(new_structure)
    present_structure = copy.deepcopy(past_structure)
    for ID in past_structure.keys():
        if ID == '': #Empty folder
            continue
        if ID in new_structure.keys():  # Hash found in the new struct
            if (past_structure[ID]['path'] == new_structure[ID]['path']): #  Nothing changed
#print("[NA]       " + past_structure[ID]['path'])
                #print past_structure[ID]['path']
                continue
            else: # Folder moved
                print(color("[MOVED]    ",'bold') + past_structure[ID]['path']+"\n" + color("-------->: ", 'bold') + new_structure[ID]['path'])
                print('Moving the folder on popcorn') #replace with actual function
                present_structure[ID]['path'] = new_structure[ID]['path']
                print('writing new struct to disk')
        else:  # Hash missing in the new struct. A) deleted or B) composition modified or C) new folder
            if(past_structure[ID]['path'] in new_paths):  # Modified
                print(color("[MODIFIED] ", 'yellow') + past_structure[ID]['path'])
                present_structure[ID] = {}  # Create new entry in present structure
                present_structure[ID]['path'] = past_structure[ID]['path']
                #Create chapter file
            else:  # No hash and no path -> Deleted
                print(color("[DELETED]  ", 'red') + past_structure[ID]['path'])
                print('writing new struct to disk')
                del present_structure[ID]
    present_paths = get_path_list(present_structure)  # Get an image of the current structure state
    for new_ID in new_structure.keys():  # Seek out new folders
        #add_to_todo_file(new_path = folder_path, what = 'create')
        if new_ID not in present_structure.keys() and new_structure[new_ID]['path'] not in present_paths: #New videos
            print(color("[NEW]      ", 'green') + new_structure[new_ID]['path'])
            print('creating new folder')
            present_structure[ID] = {}
            present_structure[ID]['path'] = new_structure[new_ID]['path']
            print('writing structure to file')
            #Create chapter file

def get_path_list(structure):
    paths = []
    for ID in structure.keys():
        paths.append(structure[ID]['path'])
    return(paths)

def add_to_todo_file(what, old_path = '', new_path = '', todo_file = '/share/Scripts/todo.sh', *args, **kwargs):
    '''
    Function that adds bash commands as strings into a file (default = /share/Scripts/todo.sh)
    '''
    ffmpeg_make = '/share/Scripts/ffmpeg-static/ffmpeg -y -xerror -f concat -i \''
    ffmpeg_remake = '/share/Scripts/ffmpeg-static/ffmpeg -y -xerror -i '
    if(what == 'move'):
        output_string = "mv \'" + popcorn_base + "/" + "/".join(old_path.split("/")[3:5]) + "/" + old_path.split("/")[-1] + ".mpeg\'" + " \'" + popcorn_base + "/" + "/".join(new_path.split("/")[3:4]) + "/" + new_path.split("/")[-1] + ".mpeg\'\n"
        #output_string += "rm " + popcorn_base + old_path + "/" + old_path.split("/")[-1] + ".mpeg"
    elif(what == "modify"):  #Modified video_list
        filename = "/" + old_path.split("/")[-1] + ".mpeg"
        output_string = "rm \'" + popcorn_base + "/" + "/".join(old_path.split("/")[3:5]) + filename + "\'\n"
        output_string += ffmpeg_make + old_path + "/video_list.txt\' -codec copy \'" + old_path + filename + "\n"
        output_string += "mv \'" + old_path + filename + "\' \'" + popcorn_base + "/" + "/".join(old_path.split("/")[3:5]) + filename +"\'\n"
    elif(what == "create"):  #New folder to create.
        output_string = ""
        if(not os.path.exists("\'" + popcorn_base + "/" + new_path.split("/")[3]) + "\'"):
            output_string += "mkdir \'" + popcorn_base + "/" + new_path.split("/")[3] + "\'\n"
        output_string += "mkdir \'" + popcorn_base + "/" + "/".join(new_path.split("/")[3:5]) + "\'\n"
        filename = "/" + new_path.split("/")[-1] + ".mpeg"
        output_string += ffmpeg_make + new_path + "/video_list.txt\' -codec copy \'" + new_path + filename + "\'\n"
        output_string += "mv \'" + new_path + filename + "\' \'" + popcorn_base + "/ " + "/".join(new_path.split("/")[3:5]) + filename + "\'\n"
    elif(what == "delete"): # Delete folder
        output_string = "rm -r \'" + popcorn_base + "/".join(old_path.split("/")[3:5]) + "\'\n"
    with open(todo_file, "a") as file_list:
        file_list.write(output_string.encode("utf-8"))

def exec_todo(file_to_exec='/share/Scripts/todo.sh'):
    '''
    Function that runs each lines of todo.sh
    '''
    while 1:
        with open(file_to_exec,'r') as f:
            first = f.readline()
            if(first == ''):
                break
            sub = subprocess.Popen(first, shell = True)
            sub.wait()
            if(sub.wait() == 1 and 'concat' in first):
                print 'this should be reworked'


            if(sub.wait() != 0):
                print sub.wait()
        out = subprocess.Popen("sed '1d' " + file_to_exec + " > /share/Scripts/tmpfile; mv tmpfile " + file_to_exec, shell = True)
        out.wait()
    print("file done")

def create_chapters_list(chapters_duration, folder_path):
    '''
    Function that creates a file containning the file list and the duration of the videos to create a new video
    Takes a folder in entry, creates a file
    '''
    output_string = ''
    duration_file = ''
    previous = ''
    for n,filename in enumerate(sorted(chapters_duration)):
        if (n == 0): #First Video
            output_string += '{}\n00:00:{}'.format(filename.encode('utf-8'),chapters_duration[filename][1])
            o = datetime.strptime(chapters_duration[filename][1],'%S.%f')
            d = datetime.strptime(chapters_duration[filename][0],'%H:%M:%S.%f')
            deltaO = timedelta(hours = o.hour, minutes = o.minute, seconds = o.second, microseconds = o.microsecond)
            deltaD = timedelta(hours = d.hour, minutes = d.minute, seconds = d.second, microseconds = d.microsecond)
            last = (deltaO + deltaD)
        else:
            o = datetime.strptime(chapters_duration[filename][1],'%S.%f')
            d = datetime.strptime(chapters_duration[filename][0],'%H:%M:%S.%f')
            deltaO = timedelta(hours = o.hour, minutes = o.minute, seconds = o.second, microseconds = o.microsecond)
            deltaD = timedelta(hours = d.hour, minutes = d.minute, seconds = d.second, microseconds = d.microsecond)
            output_string += '{}\n{}'.format(filename.encode('utf-8'),str(deltaO + last))
            last = deltaD + deltaO + last
    with open(folder_path + '/chapters.txt', 'w') as file_list:
        file_list.write(output_string.encode('utf-8'))

#Function that gets a key in a dict using its value
#Dict and key
def get_key_from_value(structure, value):
    return structure.keys()[structure.values().index(value)]


#Function that checks if A410 is mounted
#Input:NA
#Output: Bool
def mount():
    if (not os.path.exists('/mnt/A410')):
        print("making dir /mnt/A410")
        os.makedirs("/mnt/A410")
    try:
        error = subprocess.Popen("mount -t cifs //192.168.1.41/share/Video -o username=nmt,password=12345 /mnt/A410/")
        if error == 0:
            print("Mounted!")
            return True
    except:
        print("Mount failed")
        return True
        exit()
    return True
    return os.path.ismount('/mnt/A410')

#Function that takes a filepath and returns a string ID for this file
#Input: Filepath as string
#Output: ID as string
def create_file_id(filepath):
    file_name = filepath.rsplit('/', 1)[1]
    print(file_name)
    with open(filepath) as f:
        return file_name + md5_for_file(f)


#Function that takes a file and tells if its a video or not
#Input: File
#Output: File or nothing
def check_if_vid(f):
    extension_list = ['.mp4', '.mpg', '.mpeg', '.avi', '.tod', '.vob', '.wmv', '.mkv']
    for ext in extension_list:
        if(f.endswith(ext) or f.endswith(ext.upper())):
            return True
    else:
        return False
#Function that converts gets rid of any accents in a string and returns the same string without it.
def remove_accents(input_str_raw):
    encoding = "utf-8"
    input_str = input_str_raw.decode(encoding)
    nkfd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])



def dev():
    struct = read_structure_from_file('dir_tree.txt')
    new_struct = create_structure(root_level)
    return(struct, new_struct)
#Main
########################################################################################################################################
#See if structure file "dir_tree.txt" exists
if __name__ == "__main__":
    if (mount()):
        try:
            open('dir_tree.txt', 'r')
        except:
            print("dir_tree.txt not found")
            structure = create_structure(root_level)
            write_structure(structure)
        else:
            structure = read_structure_from_file('dir_tree.txt')
        #Test for changes
        new_structure = create_structure(root_level)
        if(structure == new_structure):
            print("Nothing has changed")
        else:
            print("finding changes")
            diff_structure(structure, new_structure)

        #structure = create_structure(root_level)
        #write_structure(structure)
        #pprint(structure)
