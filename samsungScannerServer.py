#!/usr/bin/env python
#
# Tool to interact with the "scan to PC" option in Samsung MFP like the CLX 3300
#
# Version 0.2
# By angelnu (1/2013)
#
# Version 0.3.0
# Bug fixes and enhancement 
# optimized for Samsung CLX-3305W (<Vid>04e8</Vid><Pid>3456</Pid>)
# By totally-king (3/2013)
#    (search 't-k:')
#
# Version 0.4.5
# By angelnu and totally-king (08/2013)
#
# Dependencies: python-imaging-sane, python-pysnmp-common, python-pypdf, scanner working in sane
#                              #t-k: python-pysnmp4 is the test replacement only in quantal,
                               #     but virtual package ...-common also exists
#for python2
from __future__ import print_function

__version__ = "0.4.5"

import pysnmp
#for python2
from six.moves import http_client
import re
import time
import xml.etree.ElementTree as ET
import signal
import os
import os.path
from string import Template
import datetime
from PIL import Image
#Circumvention for PDF save BUG
#https://github.com/python-imaging/Pillow/issues/215
#Found in Ubuntu 13.10
try:
  import pkg_resources
  if (pkg_resources.get_distribution("pillow").version == '2.0.0'):
    print("Using circumvention for PDF save because you use pillow 2.0.0")
    Image.init()
    orgPDFSave=Image.SAVE["PDF"]
    def myPDF_save(im, fp, filename):
        print(im.encoderconfig)
        # get keyword arguments
        im.encoderconfig = (
            0,#quality,
            0,#"progressive" in info or "progression" in info,
            0,#info.get("smooth", 0),
            0,#"optimize" in info,
            0,#info.get("streamtype", 0),
            0,0,#dpi[0], dpi[1],
            0,#subsampling,
            None)#qtables
        orgPDFSave(im, fp, filename)
    Image.register_save("myPDF", myPDF_save)
    Image.register_extension("myPDF", ".pdf")
except Exception:
    None

from PIL import ImageOps
import sane
import sys, traceback
import logging
import logging.handlers
import platform
from optparse import OptionParser, OptionGroup
from PyPDF3 import PdfFileWriter, PdfFileReader
import io
import atexit
import pwd #t-k: for automatically configured OUTPUT_PREFIX and OWNER(_UID)
import signal #t-k: for correct handling of SIGTERM and so on (which atexit can't handle)
import socket #t-k: needed for TCP and UDP proxy to interfere with scanner commands needed for multipage
import multiprocessing #t-k: need subprocesses for TCP and UDP proxy
from urllib import request
try:
    import queue
except ImportError:
   #for python2
   import Queue as queue
import threading #t-k: needed for QueueListener thread that handles logging
import errno #t-k: needed for error handling in TCP proxy


"""
Summary of messages exchanged in order to scan

register server: server -> scanner (HTTP POST) with:
<?xml version="1.0" encoding="UTF-8" ?>
<root>
<S2PC_Regi UserID="Server-XP" UniqueID="ac16b1c1824380e7" RegiType="ADD" />
</root>

scanner answer:
<?xml version="1.0" encoding="UTF-8"?><root><S2PC_Regi UserID ="Server-XP" Result="ADD_OK" InstanceID="27" /></root>

query SNMP 1,3,6,1,4,1,236,11,5,11,81,11,7,2,1,2,<InstanceID> until is we get "1" in the first byte (user selected the server to scan).
Samsung Windows driver does this every 1/2 second

send configuration options to scan: sever -> scanner (HTTP Post) with:
<?xml version="1.0" encoding="UTF-8" ?>
<root>
    <S2PC_AppList>
        <List>
            <AppIndex Value="1" />
            <AppName Value="My Documents" />
            <AppType Value="MAC" />
            <Resolution Value="DPI_300" />
            <Color Value="COLOR_GRAY" />
            <FileFormat Value="FORMAT_M_PDF" />
            <ScanSize Value="SIZE_A4" />
            <DuplexScan Value="DUPLEX_OFF" />
            <Orientation Value="ORIENTATION_SIDEWAY" />
        </List>
    </S2PC_AppList>
</root>

scanner answer:
closes connection

query SNMP 1,3,6,1,4,1,236,11,5,11,81,11,7,2,1,2,<InstanceID> until is we get "2" in the first byte (user has selected scan options based on the offered template).

start a scan using SANE

register server again

if we want to unregister the server: sever -> scanner (HTTP Post) with:
<?xml version="1.0" encoding="UTF-8" ?>
<root>
<S2PC_Regi UserID="Server-XP" UniqueID="ac16b1c1824380e7" RegiType="DELETE" />
</root>

"""

############################## FUNCTIONS ###############################


#HTTP Post functions

def post_multipart(host, selector, fields, files, expectResponse=True):
    """
    Post fields and files to an http host as multipart/form-data.
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return the server's response page.
    """
    #t-k: print a better error message to the log
    try:
        content_type, body = encode_multipart_formdata(fields, files)
        h = http_client.HTTPConnection(host)
        #h.set_debuglevel(1)
        h.putrequest('POST', selector)
        h.putheader('content-type', content_type)
        h.putheader('content-length', str(len(body)))
        h.endheaders()
        h.send(body)
        if expectResponse:
            response = h.getresponse()
            return response.read()
        else:
            return None
    except Exception as e:
        raise Exception('Problem contacting Scanner over network: %s' % e)

def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = b'----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = b'\r\n'
    L = []
    for (key, value) in fields:
        L.append(b'--' + BOUNDARY)
        L.append(b'Content-Disposition: form-data; name="%d"' % key)
        L.append(b'')
        if type(value) != bytes:
            value = value.encode("utf-8")
        L.append(value)
    for (key, filename, value) in files:
        L.append(b'--' + BOUNDARY)
        L.append(b'Content-Disposition: form-data; name="%d"; filename="%b"' % (key, filename.encode("utf-8")))
        L.append(b'Content-Type: application/octet-stream')
        L.append(b'')
        if type(value) != bytes:
            value = value.encode("utf-8")
        L.append(value)
    L.append(b'--' + BOUNDARY + b'--')
    L.append(b'')
    body = CRLF.join(L)
    content_type = b'multipart/form-data; boundary=%b' % BOUNDARY
    return content_type, body


def registerServer(printing=True):
    MSG  = '<?xml version="1.0" encoding="UTF-8" ?>'
    MSG += '<root>'
    MSG += '<S2PC_Regi UserID="'+SERVER_NAME+'" UniqueID="'+SERVER_UID+'" RegiType="ADD" />'
    MSG += '</root>'

    result = str(post_multipart(SCANNER_IP,'/IDS/ScanFaxToPC.cgi',[],[(1,"c:\IDS.XML",MSG)]))
    #print result
    #<?xml version="1.0" encoding="UTF-8"?><root><S2PC_Regi UserID ="W510" Result="ADD_OK" InstanceID="29" /></root>

    m = re.match('.*Result="ADD_OK" InstanceID="(\d+)"', result)
    if not m:
        raise NameError("Error registering server: "+result)
    else:
        if printing:
            print("Newly registered server '%(SERVER_NAME)s' with UniqueID '%(SERVER_UID)s' has got" % globals())
            print("    InstanceID '" + m.group(1) + "'.") #t-k: better readability and understanding
        return int(m.group(1))


#t-k: restructered function to be real refresh
def refreshServer():
    global SERVER_INSTANCE_ID
    oldInstanceID = SERVER_INSTANCE_ID
    SERVER_INSTANCE_ID = registerServer(printing=False)
    if SERVER_INSTANCE_ID != oldInstanceID:
        print("Refreshed server '%(SERVER_NAME)s' with UniqueID '%(SERVER_UID)s' has got" % globals())
        print("    new InstanceID '" + str(SERVER_INSTANCE_ID) + "'.")
    return SERVER_INSTANCE_ID


#t-k: new function = easier to understand
def unregisterServer():
    uniqueID=SERVER_UID
    MSG  = '<?xml version="1.0" encoding="UTF-8" ?>'
    MSG += '<root>'
    MSG += '<S2PC_Regi UserID="'+SERVER_NAME+'" UniqueID="'+uniqueID+'" RegiType="DELETE" />'
    MSG += '</root>'

    result = post_multipart(SCANNER_IP,'/IDS/ScanFaxToPC.cgi',[],[(1,"c:\IDS.XML",MSG)])
    #print result
    #<?xml version="1.0" encoding="UTF-8"?><root><S2PC_Regi UserID ="server" Result="DELETE_OK" InstanceID="140" /></root>
    
    m = re.match(b'.*Result="DELETE_OK"', result)
    if not m:
        raise NameError("Error unregistering server: "+result)
    else:
        print("Unregistered server '%(SERVER_NAME)s' with UniqueID '%(SERVER_UID)s'." % globals())
    

def pushServerOptions():
    """<?xml version="1.0" encoding="UTF-8" ?>
       <root>
         <S2PC_AppList>
           <List>
            <AppIndex Value="1" />
            <AppName Value="Gray default" />
            <AppType Value="MAC" />
            <Resolution Value="DPI_300" />
            <Color Value="COLOR_GRAY" />
            <FileFormat Value="FORMAT_M_PDF" />
            <ScanSize Value="SIZE_A4" />
            <DuplexScan Value="DUPLEX_OFF" />
            <Orientation Value="ORIENTATION_SIDEWAY" />
          </List>
        </S2PC_AppList>
     </root>"""
    root = ET.Element('root')
    appList = ET.SubElement(root, 'S2PC_AppList') 

    index=0
    for option in OPTIONS:
        index+=1
        listElement = ET.SubElement(appList, 'List')
        ET.SubElement(listElement, 'AppIndex').attrib['Value']=str(index)
        ET.SubElement(listElement, 'AppName').attrib['Value']=option["name"]
        ET.SubElement(listElement, 'AppType').attrib['Value']='MAC'
        ET.SubElement(listElement, 'Resolution').attrib['Value']=option["resolution"]
        ET.SubElement(listElement, 'Color').attrib['Value']=option["color"]
        ET.SubElement(listElement, 'FileFormat').attrib['Value']=option["format"]
        ET.SubElement(listElement, 'ScanSize').attrib['Value']=option["size"]
        ET.SubElement(listElement, 'DuplexScan').attrib['Value']="DUPLEX_OFF"
        ET.SubElement(listElement, 'Orientation').attrib['Value']="ORIENTATION_SIDEWAY"
    
    MSG=b'<?xml version="1.0" encoding="UTF-8" ?>\r\n'+ET.tostring(root)
    #MSG=ET.tostring(root, encoding="UTF-8")
    result = post_multipart(SCANNER_IP,'/IDS/ScanFaxToPC.cgi',[],[(1,"scantopc",MSG)],False)


def queryUserOptions():
    result = post_multipart(SCANNER_IP,'/IDS/UserSelect.xml',[],[(1,"scantopc","")])
    #{'name':'Gray-S_PDF-75','color':'GRAY','resolution':'75','format':'S_PDF','size','a4'}
    #result='<?xml version="1.0" encoding="UTF-8"?><root><S2PC_Select><AppIndex Value="1"/><Resolution Value="DPI_300"/><Color Value="COLOR_GRAY"/><FileFormat Value="FORMAT_M_PDF"/><ScanSize Value="SIZE_A4"/></S2PC_Select></root>'
    #print result
    root = ET.fromstring(result).find('S2PC_Select')
    index = root.find('AppIndex').attrib["Value"]
    
    user_options=OPTIONS[int(index)-1] #t-k: added '-1'
    user_options['color']=root.find('Color').attrib["Value"]
    user_options['resolution']=root.find('Resolution').attrib["Value"]
    user_options['format']=root.find('FileFormat').attrib["Value"]
    user_options['size']=root.find('ScanSize').attrib["Value"]

    return user_options



#SNMP queries

def querySNMPVariable(ip,oid):
    from pysnmp.entity.rfc3413.oneliner import cmdgen

    errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(
      cmdgen.CommunityData('my-agent', 'public', 0),
      cmdgen.UdpTransportTarget((ip, 161)),
      oid)

    returnValue=None
    if errorIndication:
       raise NameError('Error indication in SNMP query: %s' % errorIndication) #t-k: %s to avoid TypeError
    elif errorStatus:
       raise NameError('Error status in SNMP query: %s' % errorStatus) #t-k: %s to avoid TypeError
    else:
       returnValue=varBinds
    return returnValue


def queryPrinterScanStatus(instanceID):
    #t-k: more descriptive Error handling and logging
    try:
        result = querySNMPVariable(SCANNER_IP,(1,3,6,1,4,1,236,11,5,11,81,11,7,2,1,2,instanceID))
        #(ObjectName('1.3.6.1.4.1.236.11.5.11.81.11.7.2.1.2.29'), OctetString('\x00\x00\x00\x00'))
        return result[0][1][0]
    except Exception as e:
        if 'result' not in locals():
            result = None
        raise Exception(("Could not query printer scan status.\n" + ' '*4 + \
                               "Result was '%(result)s'.\n" + ' '*4 + \
                               "Error message: %(e)s.") % locals())


#Function for a single scan task
def scannWorker():

    refreshServer()

    #t-k: a little more descriptive logging
    print("Waiting for scan job ...")
    #print ' '*4 + 'printer scan status: ' + str(queryPrinterScanStatus(SERVER_INSTANCE_ID)) + ' -- waiting for 1 ...'
    i=0
    while (queryPrinterScanStatus(SERVER_INSTANCE_ID) != 1):
        i+=1
        if (i%300 == 0): #t-k: refresh every > 5 mins (server get's auto. unregistered after ~30 mins)
            refreshServer()
        time.sleep(1)
    print(' '*4 + 'Got it!')

    pushServerOptions()

    #t-k: a little more descriptive logging
    print("Waiting for user selection ...")
    #print ' '*4 + 'printer scan status: ' + str(queryPrinterScanStatus(SERVER_INSTANCE_ID)) + ' -- waiting for 2 ...'

    #t-k: may be canceled by user: check if status changes back to 1
    i = 0
    while True:
        pps = queryPrinterScanStatus(SERVER_INSTANCE_ID)
        if pps == 2:
            break
        elif pps == 1:
            pushServerOptions()
            print('Reconnected, waiting for user selection ...')
            #print ' '*4 + 'printer scan status: ' + str(queryPrinterScanStatus(SERVER_INSTANCE_ID)) + ' -- waiting for 2 ...'
            continue
        i += 1
        if i%300 == 0:
            refreshServer()
        time.sleep(1)
    print(' '*4 + 'Got it!')

    user_selection = queryUserOptions()
    print('Options selected by user:', user_selection)
    
    scanAndSave(user_selection)

#t-k: method to automatically determine translation from scanner command (received by server) to sane command
#     was written for sizes but may be adapted to other translations
def autoconfigDic(dic_name, xmlKey, preferred):
    if dic_name not in globals():
        try:
            #t-k: get available options from XML file that may be received by server
            capxmlfile = request.urlopen('http://%s/IDS/CAP.XML' % REAL_SCANNER_IP)
            capxmldata = capxmlfile.read()
            capxmlfile.close()
            xmlroot = ET.fromstring(capxmldata)
            sizes = []
            for size in xmlroot.iter(xmlKey):
                sizes.append(size.attrib['ID'])
            #t-k: get available size options for SANE device
            saneSizes = saneSingleton["page_format"].constraint
            #t-k: match these two sets together and save as dic_name (e.g. SIZE2SANE)
            dic = {}
            for sizeID in sizes:
                sizeLst = sizeID.split('_')[1:] #t-k: may be > 1 part, e.g. ['B5', 'JIS']
                candidates = []
                for saneSize in saneSizes:
                    flag = True
                    for sizeElm in sizeLst:
                        flag = flag and sizeElm.lower() in saneSize.lower()
                    #t-k: save combination if all parts match sane size and
                    #     rotated takes precedence over non-rotated
                    if flag and ( sizeID not in dic or preferred in saneSize.lower() ):
                        dic[sizeID] = saneSize
            if dic == {}:
                raise ValueError('%(dic_name)s dictionary must not be empty!' % locals())
            globals()[dic_name] = dic
            print_autoconfig(dic, dic_name, no_quotes=True)
        except Exception as e:
            print('Error while trying to configure scanning options:', file=sys.stderr)
            print('    %s: %s' % ( type(e).__name__, e ), file=sys.stderr)
            print("You should manually configure %s in '%s'." % ( dic_name, CONFIG_FILE ), file=sys.stderr)
            sys.exit(1)
 
#angelnu: my scanner takes very long to find -> cache
saneSingleton = None
def getSaneInstance():
    global saneSingleton
    if saneSingleton:
        return saneSingleton
    else:
        print("Init SANE ...")
        sane.init()

        print("Connecting to scanner ...")
        while True:
            try:
                #t-k: use modified open method to use modified sane classes
                if MODIFIED_SANE:
                    saneSingleton = modsaneopen(SCANNER_SANE_NAME)
                else:
                    saneSingleton = sane.open(SCANNER_SANE_NAME)
            except Exception as e:
                if MODIFIED_SANE and e.message.startswith('no such scan device'):
                    print("Proxy scan 'device' not found, restarting proxies and trying again ...", file=sys.stderr)
                    #t-k: restart proxies
                    exitProxies()
                    startProxies()
                else:
                    print('Problem connecting to scanner, trying again in 10s ...', file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
                    time.sleep(10)
            else:
                #t-k: if SIZE2SANE / ... haven't been given in config file, try to automatically configure them
                autoconfigDic('SIZE2SANE', 'Size', 'rotated') #t-k: f.l.t.r. -> name of dict, xml key, preferred sane option
                break
        
        print("Connected to scanner.")
        return saneSingleton
      
def scanAndSave(user_selection, imgs=None):
    global saneSingleton #t-k: if cache needs to be reset

    #t-k: to raise file index independent of file extension
    #     so no more same file names with different extensions
    def existsFileWithOtherExtension(baseFileName):
        from glob import glob
        searchPattern = baseFileName + '.*'
        return bool(glob(searchPattern))

    #t-k: change ownership of scan file
    def chownFile(fileName):
        if 'OWNER_UID' in globals():
            uid = int(OWNER_UID)
            gid = pwd.getpwuid(uid).pw_gid
            os.chown(fileName, uid, gid)
    
    #print 'Device options:   ', s.get_options()
    #print 'Device parameters:', s.get_parameters()

    mode = MODES2SANE[user_selection["color"]]
    print("MODE: "+mode)
    dpi=int(user_selection["resolution"].replace('DPI_',''))
    print("DPI: "+str(dpi))
    size=SIZE2SANE[user_selection["size"]]
    print("SIZE: "+size)
    
    #Initialize scan
    
    def initScan():
        print("Scanning ...")
        s = getSaneInstance()
        s.mode = mode
        s.resolution = dpi
        s.page_format = size #t-k: bugfix page_format is correct (not page-format)
        imgs = s.multi_scan()
        return imgs, s

    if not imgs:
        imgs, s = initScan()

    #Process images
    outputFiles=[]
    index=1
    date=datetime.datetime.now().strftime("%Y-%m-%d")
    while True:
        try:
            for im in imgs:
                fileExists=True
                while (fileExists):
                    baseFileName=Template(user_selection["output"]).safe_substitute(date=date, uid="%02d" % index, #t-k: index formatted with padding zero
                                                                                homedir=HOME_DIR) #t-k: automatically detect home dir ('~')
                    fileName=baseFileName+'.'+EXTENSIONS[user_selection["format"]] #t-k: seperate baseFileName
                    fileExists=existsFileWithOtherExtension(baseFileName) #t-k: raise index independent of file extension
                    index+=1
                #t-k: rotate image if necessary
                if re.match('.*rotate', size, re.IGNORECASE):
                    im = im.rotate(270)
                #t-k: print log of applying user filters only if there are any
                if len(user_selection['filters']):
                    print("Applying user filters to "+fileName+" ...")
                    for userFilter in user_selection['filters']:
                        im=userFilter(im) #t-k: replaced img with im
                print("Saving "+fileName+" ...")
                im.info['dpi']=(dpi,dpi)
                im.info['resolution']=(dpi,dpi)
                im.save(fileName, dpi=(dpi,dpi), resolution=dpi)
                chownFile(fileName) #t-k: change ownership of scan file
                print("Done.")
                outputFiles.append(fileName)
        except Exception as e:
            if e == 'Error during device I/O':
                if MODIFIED_SANE:
                    print('SANE ' + e + '. Restarting proxies and retrying ...', file=sys.stderr)
                    exitProxies()
                    startProxies()
                else:
                    print('SANE ' + e + '. Retrying ...', file=sys.stderr)
                #s.close() # <- this causes seg fault
                saneSingleton = None
                imgs, s = initScan()
            else:
                print('Whoops! Problem scanning (maybe version Samsung device driver >= 4.1 and multi-scan?):', file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                break
        else:
            break
    
    #t-k: if more than one server is used on the same scanner
    #     does not yet work, since closing the session raises a seg fault
    #     maybe poor programming of the C based sane extension?
    #     (not incrementing reference count when new references to scanner object are created?)
    if not SCANNER_CACHING:
        #t-k: end session with scanner and reset cache
        #s.close() # <- this causes seg fault
        saneSingleton = None
        #print('Scanner session closed and cache reset.')
        print('Scanner cache reset.')

    #Concat PDFs and delete temp ones
    if (user_selection["format"] == "FORMAT_M_PDF" or user_selection["format"] == "FORMAT_PDF") and (len(outputFiles)>1):
        print("Concatenating PDF files ...")
        output = PdfFileWriter()
        for aFile in outputFiles:
            inputPDF = PdfFileReader(file(aFile, "rb"))
            output.addPage(inputPDF.getPage(0))
        outputStream = io.BytesIO()#file(outputFiles[0], "wb")
        output.write(outputStream)
        #outputStream.close()

        for aFile in outputFiles:
            print("Deleting "+aFile+" ...")
            os.remove(aFile)

        print("Writing final PDF "+outputFiles[0]+" ...")
        outputFile=open(outputFiles[0],"wb")
        outputFile.write(outputStream.getvalue())
        outputFile.close()
        chownFile(outputFiles[0]) #t-k: change ownership of scan file
        print("Done.")

def delPIDFile():
    #t-k: delete PID only if it exists and if not caught signal SIGQUIT (3, with Strg+\)
    if CAUGHT_SIGQUIT:
        print('Did not remove PID file: ' + options.pidfile + '\n' + ' '*4 + \
                'because of the SIGQUIT signal caught.')
    else:
        if os.path.exists(options.pidfile):
            os.remove(options.pidfile)
            print('Removed PID file: ' + options.pidfile)
        else:
            print('Could not remove PID file: ' + options.pidfile + '\n' + ' '*4 + \
                        "because it was already deleted (probably by 'sudo service samsungScannerServer stop').")

def serverUIDgen():
    '''gerate a UniqueID for this server based on SERVER_NAME and hostname
       using md5 as hash method
    '''
    from hashlib import md5
    
    servername = SERVER_NAME
    hostname = platform.node()
    
    def hash2halfLength2int(hashString):
        '''convert hash string to half its length
           watch out: returns int (not str)
        '''
        half_length = int(len(hashString)/2)
        part1 = hashString[:half_length]
        part2 = hashString[half_length:]
        half_hash_int = int(part1, 16) + int(part2, 16)
        #restrict to max. 16 (hex) characters
        half_hash_int %= (256**8)
        return half_hash_int
    
    #use md5 as hash method -> length 32    
    server_hash = md5(servername.encode('utf-8')).hexdigest()
    host_hash   = md5(hostname.encode('utf-8')).hexdigest()
    server_hash_half_int = hash2halfLength2int(server_hash)
    host_hash_half_int   = hash2halfLength2int(host_hash)
    serverUID_int = server_hash_half_int + host_hash_half_int
    #restrict to max. 16 (hex) characters
    serverUID_int %= (256**8)
    #convert to hex
    serverUID = hex(serverUID_int).replace("0x","").replace("L","")
    return serverUID


########################### SIGNAL HANDLING ############################

#t-k: handle some signals to trigger normal exit (and atexit then triggers its own stuff (delPID, unregisterServer))
def sigHandler(signum, stack=None):
    sig = convSignum2Sig[signum]
    if sig in ['SIGHUP', 'SIGINT', 'SIGQUIT', 'SIGTERM']:
        exitCode = convSig2exitCode.get(sig, 1)
        print("Caught signal %d '%s', exiting with code %d ..." %(signum, sig, exitCode))
        if sig == 'SIGQUIT':
            global CAUGHT_SIGQUIT
            CAUGHT_SIGQUIT = True
        sys.exit(exitCode)
    #for other signals
    else:
        pass

#t-k: set up dictionary to convert from signal number (e.g. 15) to signal (e.g. 'SIGTERM')
convSignum2Sig = {}
#t-k: set up dictionary to convert from signal (e.g. 'SIGTERM') to proper exit code (e.g. 143)
convSig2exitCode = {
    'SIGINT':     1,
    'SIGQUIT':  131,
    'SIGTERM':  143,
    'SIGHUP':   129,
}

#t-k: handle SIG... signals correctly (like SIGTERM)
#     thus also handles 'sudo service samsungScannerServer stop'

#~ for i in [x for x in dir(signal) if x.startswith("SIG") and not x.startswith('SIG_')]:
for i in ['SIGINT', 'SIGQUIT', 'SIGTERM', 'SIGHUP']:
    try:
        signum = getattr(signal, i)
        signal.signal(signum,sigHandler)
        convSignum2Sig[signum] = i
    except RuntimeError as m:
        pass #t-k: do not consider signals like SIGKILL, which cannot be handled (by definition)

#t-k: keep track of a caught SIGQUIT, so temp. files (PID file) will not be removed
CAUGHT_SIGQUIT = False


#################### OPTIONS AND CONFIGURATION FILE ####################

#Parse options
parser = OptionParser(usage="usage: %prog [options]",
                      version="%prog "+__version__)
parser.add_option("-d", "--daemon", action='store_true', dest="daemon",
                  help="Fork a daemon")
parser.add_option("-p", "--pidfile", dest="pidfile",
                  help="File to write the daemon PID")

group = OptionGroup(parser, "Debug Options",
                    "Caution: use these options at your own risk.  "
                    "These options are expected to be only for debugging. ")

group.add_option("--imageFiles", action="append", dest="imageFiles",
                 help="Image files to process instead of scanning. When this option is used the program "+
                      "will apply the selected filters, store the result and terminate.")
group.add_option("--optionsIndex", type="int", dest="optionsIndex",default=0,
                 help="What of the OPTIONS[] to use for processing the --imageFiles.")

parser.add_option_group(group)

(options, args) = parser.parse_args()
if len(args) != 0:
    parser.error("incorrect number of arguments")


#Read configuration
PATHS=['.','/etc']
CONFIG_FILENAME='samsungScannerServer.conf'
CONFIG_FILE=None
for path in PATHS:
    try:
        filePath=path+'/'+CONFIG_FILENAME
        exec(compile(open(filePath).read(), filePath, 'exec'))
        CONFIG_FILE=filePath
        break
    except IOError:
        ""
if not CONFIG_FILE:
    print("Could not find config file ("+CONFIG_FILENAME+") in "+str(PATHS), file=sys.stderr)
    sys.exit(1)


############################### LOGGING ################################

class LogFile(object):
    def __init__(self, name=None):
        self.logger = logging.getLogger(name)
        self.buffer=""
        #StringIO.StringIO()

    def write(self, msg, level=logging.INFO):
        self.buffer+=msg
        lines=self.buffer.splitlines()
        #print>>sys.stderr,lines
        if (self.buffer.count('\n') == len(lines)):
            self.buffer=""
        else:
            #Last line was not \n terminated
            self.buffer=lines.pop()
        for line in lines:
            self.logger.log(level, line)

    def flush(self):
        for handler in self.logger.handlers:
            handler.flush()

class filterEmptyLines(logging.Filter):
    def filter(self,record):
        return (len(record.msg) != 0)

#t-k: classes that handle logging from multiple processes
#     (supporting rotating log file)

class QueueHandler(logging.Handler):
    """
    This handler sends events to a queue. Typically, it would be used together
    with a multiprocessing Queue to centralise logging to file in one process
    (in a multi-process application), so as to avoid file write contention
    between processes.

    This code is new in Python 3.2, but this class can be copy pasted into
    user code for use with earlier Python versions.
    """

    def __init__(self, queue):
        """
        Initialise an instance, using the passed queue.
        """
        logging.Handler.__init__(self)
        self.queue = queue

    def enqueue(self, record):
        """
        Enqueue a record.

        The base implementation uses put_nowait. You may want to override
        this method if you want to use blocking, timeouts or custom queue
        implementations.
        """
        self.queue.put_nowait(record)

    def prepare(self, record):
        """
        Prepares a record for queuing. The object returned by this method is
        enqueued.

        The base implementation formats the record to merge the message
        and arguments, and removes unpickleable items from the record
        in-place.

        You might want to override this method if you want to convert
        the record to a dict or JSON string, or send a modified copy
        of the record while leaving the original intact.
        """
        # The format operation gets traceback text into record.exc_text
        # (if there's exception data), and also puts the message into
        # record.message. We can then use this to replace the original
        # msg + args, as these might be unpickleable. We also zap the
        # exc_info attribute, as it's no longer needed and, if not None,
        # will typically not be pickleable.
        self.format(record)
        record.msg = record.message
        record.args = None
        record.exc_info = None
        return record

    def emit(self, record):
        """
        Emit a record.

        Writes the LogRecord to the queue, preparing it for pickling first.
        """
        try:
            self.enqueue(self.prepare(record))
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

def listener_configurer():
    if not options.daemon:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.INFO, filename='/dev/null')
    if LOG_NAME:
        root = logging.getLogger()
        h = logging.handlers.RotatingFileHandler(filename=LOG_NAME, maxBytes=LOG_MAXBYTES, backupCount=LOG_BACKUPCOUNT)
        f = logging.Formatter(fmt='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',datefmt='%m-%d-%y %H:%M:%S')
        fil = filterEmptyLines()
        h.setFormatter(f)
        h.addFilter(fil)
        root.addHandler(h)

# This is the listener process top-level loop: wait for logging events
# (LogRecords)on the queue and handle them, quit when you get a None for a 
# LogRecord.
def listener_process(queue, configurer):
    configurer()
    while True:
        try:
            record = queue.get()
            if record is None: # We send this as a sentinel to tell the listener to quit.
                break
            logger = logging.getLogger(record.name)
            logger.handle(record) # No level or filter logic applied - just do it!
        except (KeyboardInterrupt, SystemExit):
            #raise
            pass ## handled by signal and atexit
        except:
            import sys, traceback
            print('Whoops! Problem:', file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

def worker_configurer(queue):
    h = QueueHandler(queue) # Just the one handler needed
    root = logging.getLogger()
    root.addHandler(h)
    root.setLevel(logging.INFO)


if __name__ == '__main__':

    #Daemon mode
    if options.daemon:
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError as e:
            logging.exception("Error forking daemon: %s" % e)
            sys.exit(1)
    
    #t-k: Logging supporting multiprocessing
    logQ = multiprocessing.Queue()
    listener = multiprocessing.Process(target=listener_process,
                                       args=(logQ, listener_configurer))
    listener.start()
        
    worker_configurer(logQ)
    
    sys.stdout = LogFile('stdout')
    sys.stderr = LogFile('stderr') 

    def exitListener():
        logQ.put_nowait(None)
    
    #Print version
    print("###########################")
    print("# Initiating version "+__version__)
    print("###########################")

    print('At program termination joining log listener process with:\n' + ' '*4 + \
                str(atexit.register(exitListener)))

    #Logging configuration file
    print("Used '%s' as configuration file." % CONFIG_FILE)
    print('Below is what was configured with it.')
    f=open(CONFIG_FILE)
    for line in f:
        #t-k: do not print empty lines to logfile
        if line.strip() == '':
            continue
        #t-k: do not print lines that are commented out to logfile
        noindentLine = line.lstrip()
        if noindentLine[0] == '#':
            continue
        #t-k: remove remaining comments from line
        if '#' in line:
            line = line.split('#')[0] + '\n'
        sys.stdout.write("CONFIG: "+line)
    f.close()
    
    
    #Debug mode
    if options.imageFiles:
        print("Running in debug mode!")
        HOME_DIR="/tmp/"
        imgs=[]
        for imageFile in options.imageFiles:
            imgs.append(Image.open(imageFile))
        scanAndSave(OPTIONS[options.optionsIndex], imgs)
        sys.exit(0)

    #Daemon mode
    if options.daemon and options.pidfile:
        print("Write PID to file: "+options.pidfile)
        print('At program termination removing PID file (if it still exists and not caught SIGQUIT) with:\n' + ' '*4 + \
                    str(atexit.register(delPIDFile)))
        pid = str(os.getpid())
        file(options.pidfile,'w+').write("%s\n" % pid)


########################## AUTO CONFIGURATION ##########################

#t-k: some automatic configuration providing default values
#     which takes place if values were not given in conf file

print('The following was automatically configured.')

#t-k: Automatic configuration -> Log
def print_autoconfig(variable, variable_name, no_quotes=False):
    '''add automatically configured VARIABLE to a list that is later 
       printed to log'''
    if no_quotes:
        quote = ""
    else:
        quote = "'"
    print("AUTOCONFIG: %(variable_name)s = %(quote)s%(variable)s%(quote)s" % locals())

#t-k: function to extract valid IPv4s
def extractIPs(fileContent):
    pattern = r"((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)([ (\[]?(\.|dot)[ )\]]?(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3})"
    ips = [each[0] for each in re.findall(pattern, fileContent)]
    #print(ips)
    for item in ips:
        location = ips.index(item)
        ip = re.sub("[ ()\[\]]", "", item)
        ip = re.sub("dot", ".", ip)
        ips.remove(item)
        ips.insert(location, ip)
    return ips

#t-k: Get scanner name automatically, try again if nothing found (e.g. no network connection)
if not 'SCANNER_SANE_NAME' in globals():
    while True:
        print("Init SANE ...")
        sane.init() #t-k: bugfix, can't find any devs without init
        devs = sane.get_devices()
        for dev in devs:
            if dev[1].upper() == 'SAMSUNG':
                SCANNER_SANE_NAME=dev[0]
                print_autoconfig(SCANNER_SANE_NAME, 'SCANNER_SANE_NAME')
                break
        if not 'SCANNER_SANE_NAME' in globals():
            if devs:
                tmpinsert=' SAMSUNG'
            else:
                tmpinsert=''
            sys.stderr.write('No%s Scanner found. Trying again in 30s.\n' % tmpinsert)
            time.sleep(30)
        else:
            break

if not 'SERVER_NAME' in globals():
    SERVER_NAME=platform.node() #t-k: = hostname
    print_autoconfig(SERVER_NAME, 'SERVER_NAME')

if 'OWNER_UID' in globals():
    if 'OWNER' in globals():
        pass
    else:
        OWNER=pwd.getpwuid(OWNER_UID).pw_name
        print_autoconfig(OWNER, 'OWNER')
else:
    if 'OWNER' in globals():
        OWNER_UID=pwd.getpwnam(OWNER).pw_uid
        print_autoconfig(OWNER_UID, 'OWNER_UID')
    else:
        OWNER_UID=1000 #t-k: first ubuntu user as default
        print_autoconfig(OWNER_UID, 'OWNER_UID')
        OWNER=pwd.getpwuid(OWNER_UID).pw_name
        print_autoconfig(OWNER, 'OWNER')

#t-k: always automatically retrieve home dir and extract IP
HOME_DIR=pwd.getpwuid(OWNER_UID).pw_dir
print_autoconfig(HOME_DIR, 'HOME_DIR')
#t-k: updated IP extraction method (thanks to frankentux)
try:
    SCANNER_IP = extractIPs(SCANNER_SANE_NAME)[0]
except IndexError: # regex failed?
    print("Couldn't recognize IPv4 of scanner '%s'." % SCANNER_SANE_NAME, file=sys.stderr)
    sys.exit(1)
print_autoconfig(SCANNER_IP, 'SCANNER_IP')
REAL_SCANNER_IP=SCANNER_IP #t-k: preserve IP if changed by MODIFIED_SANE method

#t-k: get own server IP and change scanner name to include that
#     (so later sane connects to scanner via proxy not directly)
if MODIFIED_SANE:
    print('Getting server IP and setting scanner name so that SANE uses proxy.')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    while True:
        try:
            sock.connect((SCANNER_IP, 80))
        except socket.error as e:
            if e.errno == errno.EALREADY: ## operation already in progress
                time.sleep(1)
                continue
            if isinstance(e, socket.timeout):
                sock.close()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
            sys.stderr.write('Problem contacting Scanner over network: %s, retrying in 10s ...\n' % e)
            time.sleep(10)
        else:
            break
    ## only way to get server IP without knowing network device name
    ##     which IP connects to scanner? (/etc/hosts not working because: hostname 127.0.0.1)
    SERVER_IP = sock.getsockname()[0]
    sock.close()
    del sock
    print_autoconfig(SERVER_IP, 'SERVER_IP')
    SCANNER_SANE_NAME = ' '.join( SCANNER_SANE_NAME.split(' ')[:-1] + [SERVER_IP] )
    print_autoconfig(SCANNER_SANE_NAME, 'SCANNER_SANE_NAME')

#t-k: check to see if scanning directory exists to create it if neccessary
#angelnu: support scanning outside home
dirsToMake=Template(OUTPUT_PREFIX).safe_substitute(homedir=HOME_DIR).split('/')[1:-1]
for i in range(1, len(dirsToMake)):
    dirToMake = "/"+"/".join(dirsToMake[0:i+1])
    if os.path.lexists(dirToMake):
        if not os.path.isdir(dirToMake):
            raise OSError('Invalid OUTPUT_PREFIX given in configuration file.\n' + \
                    ' '*9 + 'The path specified exists, but is not a directory!\n' + \
                    ' '*9 + "You should either change OUTPUT_PREFIX or check '%s' and move or rename it." % dirToMake)
    else:
        os.mkdir(dirToMake)
        uid = int(OWNER_UID)
        gid = pwd.getpwuid(uid).pw_gid
        os.chown(dirToMake, uid, gid)
        print("Created the directory '%s'." % dirToMake)

if __name__ == '__main__':
    
    #Is enabled?
    if not ENABLED_SERVER:       
        print("Server not enabled")
        sys.exit(0)


################################ CLASSES ################################

#t-k: class that handles hex messages
class HexMessage(object):
    '''instances can store, return and prettyprint hex messages'''
    
    def __init__(self, hexIn, rawIn=False, enlargeTo=False):
        '''hexIn should be either in the form '1b:a8:13:fb' or 
           '1b a8 13 fb' (rawIn=False, default) or as decoded python  
           character string '\x1b\xa8\x13\xfb' (rawIn=True)
           
           default message size is length of hexIn, set enlargeTo > 0
           to enable enlarging with zero bytes, e.g. enlargeTo=255 to
           end up with message length of at least 255 bytes'''
        if rawIn:
            msg = hexIn
        else:
            msg = hexIn.replace(':', '').replace(' ', '').replace('\n', '')
            msg = msg.decode('hex_codec')
        if enlargeTo:
            bytesLeft = enlargeTo - len(msg)
            self.msg = (msg + '\x00'*bytesLeft)
        else:
            self.msg = msg
    
    def getMsg(self):
        '''return hex message as decoded character string'''
        return self.msg
    
    def startswith(self, prefix, start=0, end=sys.maxsize):
        '''analogous to str.startswith, takes HexMessage instance as prefix
           might also be a tuple of HexMessage instances'''
        if isinstance(prefix, tuple):
            msgLst = []
            for p in prefix:
                msgLst.append(p.getMsg())
            prefix = tuple(msgLst)
        else:
            prefix = prefix.getMsg()
        return self.msg.startswith(prefix, start, end)
    
    def __eq__(self, other):
        return self.msg == other.getMsg()

    def __hash__(self):
        return hash(self.msg)
    
    def __str__(self):
        msg_encoded = self.msg.encode('hex_codec')
        res = ''
        for i in range(2, len(msg_encoded)+1, 2):
            res += msg_encoded[i-2:i] + ' '
            if (i % 10) == 0:
                res += ' '
            if (i % 40) == 0:
                res += '\n'
        return res.rstrip(' \n')


#t-k: proxy subprocess classes

class ProxyError(Exception):
    '''exception to raise for handling proxy specific errors'''
    pass


class ProxyProcess(multiprocessing.Process):
    '''a subprocess that acts as a man in the middle (MITM) proxy between 
       scanner and workstation, so it can interfere with the messages 
       being sent back and forth'''
    BUFFERSIZE = 1240
    SERVER_IP = ''
    SCANNER_IP = SCANNER_IP
    DEBUGLEVEL = PROXY_DEBUGLEVEL ## 0 -> no | 1 -> a bit | 2 -> a bit more | 3 -> lots of printing
       
    def __init__(self):
        super(ProxyProcess, self).__init__()
        self._stoprequest = multiprocessing.Event()
    
    def join(self, timeout=None):
        self._stoprequest.set()
        super(ProxyProcess, self).join(timeout)
    
    def _printLog(self, debugLevel, *content):
        '''debugLevel -> of this log entry'''
        if self.DEBUGLEVEL >= debugLevel:
            print(str(self.__class__).split('.')[1][:-2] + ':', end=' ')
            for element in content[:-1]:
                print(element, end=' ')
            print(content[-1])


class UDProxy(ProxyProcess):
    '''MITM UDP proxy on port 161 (SNMP)'''
    PORT = 161
    PROTOCOL = 'UDP'
    
    def __init__(self):
        super(UDProxy, self).__init__()
        self.serverConn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.serverConn.bind((self.SERVER_IP, self.PORT))
        self.serverConn.settimeout(1.0)
        self.clientConn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    def run(self):
        self._printLog(1, 'Initated server listening on port %d (%s) ...' % ( self.PORT, self.PROTOCOL ))
        self._printLog(1, 'Initiated client connection to scanner port %d (%s) ...' % ( self.PORT, self.PROTOCOL ))
        while not self._stoprequest.is_set():
            try:
                fromWS, addrWS = self.serverConn.recvfrom(self.BUFFERSIZE)
                self._printLog(3, 'received %4d bytes from %s:%5d' % ( len(fromWS), addrWS[0], addrWS[1] ))
            except socket.timeout:
                continue
            self.serverConn.settimeout(None)
            sentSizeClient = self.clientConn.sendto( fromWS, (self.SCANNER_IP, self.PORT) )
            self._printLog(3, 'sent     %4d bytes to   %s:%5d' % ( sentSizeClient, self.SCANNER_IP, self.PORT ))
            fromScanner, addrSc = self.clientConn.recvfrom(self.BUFFERSIZE)
            self._printLog(3, 'received %4d bytes from %s:%5d' % ( len(fromScanner), addrSc[0], addrSc[1] ))
            sentSizeServer = self.serverConn.sendto( fromScanner, (addrWS[0], addrWS[1]) )
            self._printLog(3, 'sent     %4d bytes to   %s:%5d' % ( sentSizeServer, addrWS[0], addrWS[1] ))
            self.serverConn.settimeout(1.0)
        ## execute when process is joined (closed)
        self.serverConn.close()
        self.clientConn.close()
        self._printLog(1, 'closed!')


class TCProxy(ProxyProcess):
    '''MITM TCP proxy on port 9400'''
    PORT = 9400
    PROTOCOL = 'TCP'
    SRCPORT = 0 #2270 ## for client connection with scanner, set to 0 if dynamic source port wanted
    
    def __init__(self, queryQ, resultQ):
        super(TCProxy, self).__init__()
        self.queryQ = queryQ
        self.resultQ = resultQ
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.SERVER_IP, self.PORT))
        self.server.listen(1)
        self.server.settimeout(1.0)
        self.clientConn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.SRCPORT:
            self.clientConn.bind((self.SERVER_IP, self.SRCPORT))
        self.npRequest = HexMessage('1b a8 20 fb 01 2c 01', enlargeTo=255) ## np = next page
    
    def _checkNextPageStatus(self):
        pleaseWait  = HexMessage('a8 08 00 00 00 f9 00 00 01 00 1e', enlargeTo=255)
        yesNewPage  = HexMessage('a8 00 00 00 00 f9 00 00 01 00 1e', enlargeTo=255)
        noMorePages = HexMessage('a8 04 00 00 00 f9 00 00 01 00 1e', enlargeTo=255)
        canceling   = HexMessage('a8 04 f9 00 00 00 00 01',          enlargeTo=255)
        result = None
        self.clientConn.settimeout(1.0)
        while not self._stoprequest.is_set():
            try:
                sentSizeClient = self.clientConn.send(self.npRequest.getMsg())
                self._printLog(3, 'checking if there are more pages to come ...')
                self._printLog(3, 'sent     %4d bytes to   scanner' % ( sentSizeClient ))
                self._printLog(3, str(self.npRequest).split('\n')[0])
                fromScanner = self.clientConn.recv(self.BUFFERSIZE)
                frScHxMsg = HexMessage(fromScanner, rawIn=True)
                self._printLog(3, 'received %4d bytes from scanner' % ( len(fromScanner) ))
                self._printLog(3, str(frScHxMsg).split('\n')[0])
            except socket.timeout:
                continue
            if frScHxMsg == pleaseWait:
                self._printLog(3, '"please wait"')
                time.sleep(0.5)
                continue
            elif frScHxMsg == yesNewPage:
                result = 'yes new page'
                self._printLog(1, '"%s"' % result)
                break
            elif frScHxMsg in [noMorePages, canceling]:
                result = 'no more pages'
                self._printLog(1, '"%s"' % result)
                break
            else:
                self._printLog(1, 'could not interpret answer from scanner,\n' + str(frScHxMsg) + '\nretrying ...')
                continue                
        self.clientConn.settimeout(None)
        return result
    
    def run(self):
        result = None
        nrConnect = 1
        error3byteMsg = HexMessage('a8 28 00')
        initMsg1 = HexMessage('1b a8 12 00') ## first sent by sane
        initMsg2 = HexMessage('1b a8 16 00') ## second sent by sane
        specMsg  = HexMessage('1b a8 13 fb', enlargeTo=255) ## not sent by sane, but needed after initMsg1
                                                            ## self.npRequest needed after initMsg2
        self._printLog(1, 'Initating server listening on port %d (%s) ...' % ( self.PORT, self.PROTOCOL ))
        ## main loop starting with connection initiation with workstation (proxy as server)
        while not self._stoprequest.is_set():
            try:
                self.serverConn, self.serverConnAddr = self.server.accept()
            except socket.timeout:
                continue
            self.serverConn.settimeout(1.0)
            self._printLog(2, 'Accepted connection nr. %d from:' % nrConnect, self.serverConnAddr)
            ## (re)connect with scanner (proxy as client) if necessary
            while not self._stoprequest.is_set():               
                try:
                    self.clientConn.connect((self.SCANNER_IP, self.PORT))
                except socket.error as e:
                    ## already connected, no need to reconnect
                    if e.errno == errno.EISCONN: 
                        pass 
                    else:
                        raise
                else:
                    self.clientConn.settimeout(None)
                    self._printLog(1, 'Initiated client connection to scanner port %d (%s) ...' % \
                                        ( self.PORT, self.PROTOCOL ))
                try:
                    self.clientConn.send('')
                except socket.error as e:
                    ## broken pipe error (remote disconnect (or not yet connected)) or
                    ##     bad file descriptor (socket already closed by self)
                    if e.errno in [errno.EPIPE, errno.EBADF]:
                        self.clientConn.close()
                        self.clientConn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        continue
                    else:
                        raise
                break
            ## actual start: get package from workstation and send to scanner
            ##     loop back here continuously to check if _stoprequest is set
            while not self._stoprequest.is_set():
                try:
                    try:
                        fromWS = self.serverConn.recv(self.BUFFERSIZE)
                    except socket.timeout:
                        try:
                            ## blocking Queue.get call that times out after 50 ms
                            query = self.queryQ.get(True, 0.05)
                        except queue.Empty:
                            continue
                        if query == 'check if page is coming':
                            result = self._checkNextPageStatus()
                            if result:
                                self.resultQ.put(result)
                        continue
                    except socket.error as e:
                        ## connection reset by peer
                        if e.errno == errno.ECONNRESET:
                            self.serverConn.close()
                            break
                        else:
                            raise
                    self.serverConn.settimeout(None)
                    self._printLog(3, 'received %4d bytes from workstation' % ( len(fromWS) ))
                    if HexMessage(fromWS, rawIn=True) == error3byteMsg:
                        self._printLog(3, error3byteMsg)
                        ## connected workstation too early before file chunk was complete
                        raise ProxyError('connected workstation too early, returning to communication with scanner')
                except ProxyError as e:
                    self._printLog(3, 'ProxyError:', e)
                    pass ## did't send these 3 bytes to scanner, continue with scanner as if nothing happened
                else:
                    sentSizeClient = self.clientConn.send( fromWS )
                    self._printLog(3, 'sent     %4d bytes to   scanner' % ( sentSizeClient ))
                    self._printLog(3, str(HexMessage(fromWS, rawIn=True)).split('\n')[0])
                    if sentSizeClient == 0:
                        nrConnect += 1
                        self.serverConn.close()
                        break
                ## 250 ms timeout for (all but 1st) data packages from scanner to come in
                self.clientConn.settimeout(0.25)
                sentSizeserver = 0
                retryAfter1240 = 0 
                sendingFile = False
                ## get package from scanner and send to workstation
                ##     loop if not timed out -> sending a file
                while not self._stoprequest.is_set():
                    try:
                        fromScanner = self.clientConn.recv(self.BUFFERSIZE)
                        self._printLog(3, 'received %4d bytes from scanner' % ( len(fromScanner) ))
                    except socket.timeout:
                        ## endless retry if the 1st package was timed out (effectively no timeout at all for 1st package)
                        if not sendingFile:
                            continue
                        ## retry 2 times if last package was 1240 bytes (effectively 3*250ms = 0.75s timeout
                        ##     for these 1240 bytes follow up packages)
                        if sentSizeserver == 1240 and retryAfter1240 < 3:
                            retryAfter1240 += 1
                            continue
                        sendingFile = False
                        self.clientConn.settimeout(None)
                        break
                    retryAfter1240 = 0
                    sentSizeserver = self.serverConn.send(fromScanner)
                    self._printLog(3, 'sent     %4d bytes to   workstation' % ( sentSizeserver ))
                    self._printLog(3, str(HexMessage(fromScanner, rawIn=True)).split('\n')[0])
                    sendingFile = True ## after 1st data package
                ## special intermediate packages needed to be sent during the beginning after initMsg1/2
                fromWSHxMsg = HexMessage(fromWS, rawIn=True)
                if fromWSHxMsg in [initMsg1, initMsg2]:
                    if fromWSHxMsg == initMsg1:
                        toSend = specMsg
                    elif fromWSHxMsg == initMsg2:
                        toSend = self.npRequest
                    sentSizeClient = self.clientConn.send( toSend.getMsg() )
                    self._printLog(3, 'sent     %4d bytes to   scanner' % ( sentSizeClient ))
                    self._printLog(3, str(toSend).split('\n')[0])
                    fromScanner = self.clientConn.recv(self.BUFFERSIZE)
                    self._printLog(3, 'received %4d bytes from scanner' % ( len(fromScanner) ))
                    self._printLog(3, str(HexMessage(fromScanner, rawIn=True)).split('\n')[0])
                self.serverConn.settimeout(1.0)
        ## execute when process is joined (closed)
        try:
            self.serverConn.close()
        except AttributeError:
            pass
        self.server.close()
        self.clientConn.close()
        self._printLog(1, 'closed!')


#t-k: modifications to sane module's scanner handling
class _ModSaneIterator(sane._SaneIterator):
    '''modified next method communicating with TCP proxy subprocess
       to enable multipage scanning'''
    def __init__(self, device):
        sane._SaneIterator.__init__(self, device)
        self.iteration = 0
    
    def __next__(self):
        try:
            if self.iteration != 0:
                print('Another page coming?')
                ## tell TCP proxy to ...
                queryQ.put('check if page is coming')
                ## get result back, with blocking Queue.get call
                result = resultQ.get(True)
                self.device.cancel()
                if result == 'yes new page':
                    pass
                elif result == 'no more pages':
                    raise StopIteration
            self.device.start()
        except sane.error as v:
            if v == 'Document feeder out of documents':
                raise StopIteration
            else:
                raise Exception('Starting scan not possible: ' + v)
        else:
            self.iteration += 1
        ## no_cancel=1: leaving scanner in some sort of limbo - scan is done,
        ##     but not finished properly - perfect for TCP proxy querying
        ##     whether there are more pages to come
        return self.device.snap(no_cancel=1)
    
    def next(self):
        return self.__next__()

class ModSaneDev(sane.SaneDev):
    '''use modified _SaneIteror class'''
      
    def multi_scan(self):
        return _ModSaneIterator(self)


def modsaneopen(devname):
    '''Open a device for scanning using modified SaneDev class'''
    new=ModSaneDev(devname)
    return new


################################# MAIN #################################


if __name__ == '__main__':

    #Calculate "ID" based on SERVER_NAME and hostname
    #t-k: use md5 hashing to get real unique IDs that take into account
    #     the whole strings rather than just the last 8 letters
    SERVER_UID = serverUIDgen()

    while (True):
        try:    
           SERVER_INSTANCE_ID = registerServer()
        except Exception as e:
            logging.exception("Network or scanner not available (%s): waiting 10s and trying again ..." % e)
            time.sleep(10) #Wait 10 seconds
        else:
            break

    
    #Unregister #t-k: with new function - easier to understand
    print('At program termination unregistering server with:\n' + ' '*4 + \
                str(atexit.register(unregisterServer)))


    #t-k: initiate queues for communication with subprocesses and
    #     start the proxy server processes
    if MODIFIED_SANE:
        
        def initQs():
            global queryQ, resultQ
            queryQ, resultQ = multiprocessing.Queue(), multiprocessing.Queue()
        
        initQs()
        
        def startProxies():
            global proxies
            while True:
                try:
                    proxies = [UDProxy(), TCProxy(queryQ, resultQ)]
                except socket.error as e:
                    if e.errno == errno.EADDRINUSE: ## address already in use
                        print('TCP proxy was restarted too soon, waiting 10s ...')
                        time.sleep(10)
                    else:
                        raise
                else:
                    break
            for p in proxies:
                p.start()
        
        startProxies()
        
        #angelnu proxies not defined without MODIFIED_SANE
        
        def exitProxies():
            global proxies
            for p in proxies:
                p.join()
        
        print('At program termination joining proxy processes with:\n' + ' '*4 + \
                str(atexit.register(exitProxies)))

    
    #angelnu Test the Sane connection (also works as a chache to be ready at scan time)
    #t-k: can only do this after proxies are established if modified sane method is used
    #     + only applicable if one server is used
    if SCANNER_CACHING:
        if not getSaneInstance():
            print("Could not connect to Scanner ("+SCANNER_SANE_NAME+") via SANE.", file=sys.stderr)
            sys.exit(1)

    
    #Main program: keep scanning
    while True:
        try:
            scannWorker()
        except Exception:
            logging.exception("Something awful happened! Waiting 10 seconds before trying again.")
            time.sleep(10) #Wait 10 seconds

