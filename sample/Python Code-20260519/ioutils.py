import os
import io
import numpy as np
def get_val (prompt='Enter value',default=None,evaluate=True):
    value = None
    prompt += (default is not None) * (' [%s]' %str(default)) + ' : '    
    while not value:
        value = input(prompt)
        if value == '': value = default
    if evaluate: value = eval(str(value))
    return value
def yes_to (question,default='Y'):
    "Returns true if the answer to the question starts with Y or y"
    message = question + " (Y/N) [%s]? " %(default[0].upper())
    answer = input (message)
    response = default[0].upper()=="Y"
    if len (answer) > 0:
        if response:
            response = not answer[0].upper()=="N"
        else:
            response = answer[0].upper()=="Y"
    return response

def get_case (defile=None, dir = '.'):
    "Selects a 'case' (a sub-directory) and returns its full (relative) path"
    dlist = os.listdir(dir)
    try:
        f = open(defile,'r')
        defname = f.readline().split()[0]
        f.close()
    except:
        defname = None
    opts = {}
    count = 1
    default = ''
    for item in dlist:
        key = str(count)
        val = item
        if val == defname:
            default = key
        opts[key] = val
        count +=1
    opt = opts[get_option ('Select from the following data set(s)', opts, default)]
    try:
        f = open(defile,'w')
        f.write(opt)
        f.close
    except:
        pass
    path = dir + "/" + opt
    return path

def get_stem (ext, defile=None, dir = '.'):
    "Returns the STEM name of a file from all possible STEM.ext files"
    dlist = os.listdir(dir)
    try:
        f = open(defile,'r')
        defname = f.readline().split()[0]
        f.close()
    except:
        defname = None
    opts = {}
    count = 1
    default = ''
    for item in dlist:
        words = item.split('.')
        if words[-1] == ext or (ext=='' and len(words) == 1):
            key = str(count)
            val = words[0]
            if val == defname:
                default = key
            opts[key] = val
            count +=1
    opt = opts[get_option ('Select from the following data set(s)', opts, default)]
    try:
        f = open(defile,'w')
        f.write(opt)
        f.close
    except:
        pass
    return opt
    
def get_input_file (defname, ext='dat'):
    infile = None
    while True:
        try:
            try:
                dfile = open(defname,"r")
                fname = dfile.readline().split()[0]
                message = "\nEnter stem of data set file name [%s]" %fname
                dfile.close()
                stem = input (message+" : ")
                if len (stem) == 0:
                    stem = fname
            except:
                stem = input("\nEnter stem of data set file name {Q=quit}: ")
            if stem == 'Q':
                print ("** No file opened **\n")
                return infile
            inname = stem+"."+ext
            infile = open(inname,"r")
            break
        except:
            print ("** %s does not exist **\n" %inname)
    dfile = open(defname,"w")
    dfile.write(stem)
    dfile.close()
    return infile

def read_number (file):
    line = file.readline()
    data = line.split()
    number = eval (data[-1])
    return number

def get_number (file, kbd, prompt="Enter number", minimum=None, maximum=None, default=None):
    nonumber = True
    if kbd:
        while nonumber:
            message = prompt
            if minimum is None and maximum is not None:
                message += " {<%g}" %maximum
            elif minimum is not None and maximum is None:
                message += " {>%g}" %minimum
            elif minimum is not None and maximum is not None:
                message += " {%g to %g}" %(minimum, maximum)
            if default is not None:
                message += " [%g]" %default

            string = input(message.ljust(60)+": ")
            if len(string) == 0:
                number = default
            else:
                number = eval(string)
            nonumber = number is None
            nonumber = nonumber or (minimum is not None and number < minimum)
            nonumber = nonumber or (maximum is not None and number > maximum)
        file.write(prompt.ljust(60)+": %g\n" %number)
    else:
        number = eval(file.readline().split()[-1])
    return number

def get_option (prompt, options, default=None, kbd=True, file=None):
    
    noresponse = True
    if kbd:
        print ("\n%s :-\n" %prompt)
        message = "\nEnter option [%s]" %str(default)
        message = message.ljust(61) + ": "
        for key in options:
            opt = "\t%s" %options[key]
            opt = opt.ljust(30) + "( %s )" %key
            print (opt)
        while noresponse:
            opt = input(message).upper()
            if len (opt) == 0:
                opt = str(default)
            for key in options:
                if opt.upper() == key or opt.lower() == key:
                    opt = key
                    noresponse = False
                    exit
        tofile = "%s is %s" %(prompt, options[opt].lower())
        if file is not None:
            file.write(tofile.ljust(60)+": %s\n" %opt)
    else:
        if file is not None:
            opt = file.readline().split()[-1]
        else:
            print ("Error: No file specified")
    return opt.upper()

# Dictionary wrapper class that allows neat format and .attr referencing
class Dict:
    count = 0
    level = 0
    tab = ''
    sigfig = 5
    def __init__(self,arg=None,desc=None,conv=True):
        self.desc = desc
        if isinstance(arg, dict):
            self.unwrap(arg)
            if conv: self.npconv()
        elif isinstance(arg, str) or isinstance(arg, io.IOBase):
            self.read(arg,conv)
        Dict.count+=1
        return

    def copyattrs (self, obj):
        """Copies the attributes to the object, obj"""
        for attr in self.list():
            setattr(obj,attr,getattr(self,attr,None))
        return

    def list(self,nodesc=True):
        """Lists the first level names of attributes"""
        names = vars(self)
        attrs = []
        for key in names: attrs.append(key)
        if nodesc: attrs = attrs[1:]
        return attrs

    def delve (self, attr):
        "Recursively delves into sub-dictionaries to find the value of attr"
        attr = attr.strip()        
        if hasattr(self,attr):
            return getattr(self,attr)
        else:
            attrs = self.__dict__
            for key, val in attrs.items():
                if isinstance(val, Dict):
                    value = val.delve(attr)
                    if value is not None:
                        return value
    
    def unwrap (self, dic):
        "Unwraps a (possibly nested) dictionary, dic"
        for key, val in dic.items():
            if isinstance (val, dict):
                attr = getattr(self,key,None)
                if isinstance (attr, Dict):
                    attr.unwrap(val)
                else:
                    setattr (self,key,Dict(val))
            else:
                setattr (self,key,val)
        return
    
    def __str__(self):
        Dict.level += 1
        dic = self.__dict__
        kmax = len (max(dic.keys(),key=len))+2       
        strng = Dict.tab+"{"
        Dict.tab += '   '
        space = ''
        desc = getattr (self,'desc',None)
        strng += "\n%s%s : %s,"%(Dict.tab,repr('desc').ljust(kmax), repr(desc))
        fmt = "{:#.%dg}"%self.sigfig
        for key, value in dic.items():
            if key != 'desc' and key != 'sigfig':
                if type(value) == str:
                    strval = repr(value)
                elif type(value) == float:
                    s1 = fmt.format(value)
                    s2 = str(value)
                    strval = s1 * (len(s1)<=len(s2)) + s2 * (len(s2)<len(s1))
                elif isinstance(value,np.ndarray):
                    np.set_printoptions(threshold=np.prod(value.shape))
                    strval = repr(value)[6:-1]
                elif isinstance(value,list) and len(value) > 0 and type(value[0]) not in (int,str,float):
                    strval = '[ '
                    for item in value[:-1]:
                        strval += "\'%s\',\n%s%s"%(item.__str__(),Dict.tab,space.ljust(kmax+5))
                    strval += "\'%s\'  ]"%value[-1].__str__()
                else:
                    strval = str(value)
                strng += "\n%s%s : %s,"%(Dict.tab,repr(key).ljust(kmax), strval)
        Dict.tab = Dict.tab[:-3]
        Dict.level -= 1
        if Dict.level == 0:        
            strng = strng[:-1] + "\n}"
        else:
            strng = strng[:-1] + "}"            
        return strng

    def __repr__(self):
        return self.__str__()

    def npconv (self):
        # This converts numerical lists to np arrays (see flag "conv" in init)
        dic = vars(self)
        for key, value in dic.items():
            if isinstance(value,list):
                if len(value) > 0:
                    if not isinstance(value[0],str):
                        setattr(self,key,np.array(value))
            elif isinstance(value,Dict):
                value.npconv()
        return

    def add (self,name,dic):
        "Adds a sub-dictionary named 'name' "
        setattr (self, name, Dict(dic))
        return

    def read (self, ifile, conv=True):
        """Reads in a (possibly nested) dictionay from ifile
        which may be either the name of a file or a file object"""
        if isinstance(ifile, str):
            ifile = open(ifile)
        dic = eval(ifile.read())
        self.unwrap(dic)
        ifile.close()
        if conv: self.npconv()
        return

    def write (self, ofile):
        """Writes out a (possibly nested) dictionay to ofile
        which may be either the name of a file or a file object"""
        outf = ofile
        if isinstance(outf, str):
            outf = open(outf,"w")
        outf.write(self.__str__())
        outf.close()
        return

    def unpack (self, attrs):
        "Unpacks a list of variables defined by the comma-seprated string list, attrs"
        variables = []
        for attr in attrs.split(','):
            variables.append( getattr(self,attr.strip(),None))
        return variables

    def none (self, attrs):
        "Set list of attributes to None"
        for attr in attrs.split(','):
            attr = attr.strip()
            setattr(self,attr,None)
        return
    
    def pack (self, attrs, *argv):
        alist = attrs.split(',')
        for i in range (len(argv)):
            attr = alist[i].strip()
            setattr(self,attr,argv[i])
        return

    def put(self, attr, val):
        found = hasattr (self, attr)
        if found:
            setattr (self, attr, val)
            return found
        else:
            attrs = self.__dict__
            for key, value in attrs.items():
                if isinstance(value, Dict):
                    found = value.put (attr, val)
                    if found:
                        return found
        return found
    
    def get (self, attr):
        """Searches recursively through subdirectories to find the value
        of attr which is of the form subd1.subd2.final. If there is ambiguity
        then the first instance encountered is returned"""
        attr = attr.strip()
        bits = attr.split('.')
        poss = getattr (self,bits[0],None)
        indx = attr.find ('.')
        if len (bits) == 1 and poss is not None:
            return poss
        elif len (bits) > 1 and isinstance (poss, Dict) :
            rest = attr[indx+1:]
            return poss.get (rest)
        else:
            attrs = self.__dict__
            for key, val in attrs.items():
                if isinstance(val, Dict):
                    value = val.get (attr)
                    if value is not None:
                        return value
        return None
    
class List (list):
    """Modified version of built-in list incorporating
    a method to see if a particular value is contained within the list"""
    def __init__(self,*args):
        super().__init__()
        if len(args) == 1:
            if isinstance(args[0],list):
                alist = args[0]
            else:
                alist = [args[0]]
        else:
            alist = []
            for arg in args:
                alist.append(arg)
        self[:] = alist
        return

    def contains(self,value):
        """Returns True is value is in the List"""
        result = False
        for item in self:
            result = result or item == value
        return result

    def tostr (self):
        string = ""
        for i, val in enumerate(self):
            string += str(val)
            if i < len(self)-1 : string+=', '
        return string

    def __str__(self):
        if type(self[0]) in (int,float,str):
            return super().__str__()
        else:
            string = '[ '
            for item in self[:-1]:
                string += "\'%s\',\n  "%item.__str__()
            string += "\'%s\'  ]"%self[-1].__str__()
        return string
    
                            
