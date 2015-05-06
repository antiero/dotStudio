from __future__ import division
from xml.etree.ElementTree import parse
import os, urlparse

debug = True
def printd(str):
    global debug
    if debug:
        print(str)

def get_duration(duration_str):
    ''' Providing a time value, it returns the amount of seconds.

    If the argument was already in seconds "5s", a value of 5 will
    be returned

    If the argument is a division: "14260543/90000s", the result of
    the division will be returned.

    Note that the 's' character will be removed if it exists within
    the string.
    '''

    if duration_str.endswith('s'):
        duration_str = duration_str[:-1]

    values = duration_str.split('/')
    if len(values) > 1:
        val01, val02 = values
        val01 = int(val01)
        val02 = int(val02)
        val = None

        if val01 > val02:
            val = val01/val02
        else:
            val = val02/val01
        return val

    return float(values[0])


def get_frames_from_time(seconds, fps):
    ''' Returns the numer of frames in the amount of
    seconds specified using the framerate specified.

    '''
    return int(seconds * fps)


def timevalue_to_seconds(duration_str):
    ''' Providing a time division ex: "14260543/90000s" or a time expression
    ex: "5s", returns the amount of seconds as an integer.

    '''

    if duration_str.endswith('s'):
        duration_str = duration_str[:-1]

    values = duration_str.split('/')
    if len(values) > 1:
        val01, val02 = values
        val01 = int(val01)
        val02 = int(val02)
        val = None

        if val01 > val02:
            val = val01/val02
        else:
            val = val02/val01
        return val

    return float(values[0])


class fcpxml_wrapper(object):
    def __init__(self, filename=""):
        self.framerate = 0
        self.clip_count = None
        self.asset_count = None
        self.clips = []
        self.assets = []
        self.speeds = []

        self.read_file(filename)

    def read_file(self, filename):
        percentage = 100

        tree = parse(filename)
        root = tree.getroot()
        resources = root.find('resources')
        printd("Got resources: %s" % str(resources))

        assets = resources.findall('asset')
        printd("Got assets: %s" % str(assets))

        library = root.find('library')
        printd("Got library: %s" % str(library))

        # This needs to be changed because there can be multiple events in a library
        event = library.find('event')        
        printd("Got events: %s" % str(event))
        project = event.find('project')
        printd("Got project: %s" % str(project))
        
        mformat = resources.find('format')
        sequence = project.find('sequence')
        spine = sequence.find('spine')
        clips = (spine.findall('ref-clip') or spine.findall('clip') or
                 spine.findall('video'))

        # Get the framerate
        self.framerate = timevalue_to_seconds(mformat.get('frameDuration'))

        printd("About to check assets for '{0}'".format(filename))
        if assets:
            self.asset_count = len(assets)
            for current_asset in assets:
                asset_found = asset_wrapper()

                # TO-DO: Just tidy this up in a loop with list of needed attributes
                asset_found.id = current_asset.get('id')
                printd("Asset ID: %s " % str(asset_found.id))

                asset_found.name = current_asset.get('name')
                printd("Asset Name: %s " % str(asset_found.name))

                asset_found.uid = current_asset.get('uid')
                printd("Asset UID: %s " % str(asset_found.uid))

                asset_found.src = current_asset.get('src')
                printd("Asset src: %s " % str(asset_found.src))

                url = urlparse.urlparse(asset_found.src)
                asset_found.filepath = os.path.abspath(os.path.join(url.netloc, url.path))
                printd("Asset filepath: %s " % str(asset_found.filepath))

                asset_found.has_video = current_asset.get('hasVideo')
                printd("Asset hasVideo: %s " % str(asset_found.has_video))

                asset_found.format = current_asset.get('format')
                printd("Asset format: %s " % str(asset_found.format))

                asset_found.has_audio = current_asset.get('hasAudio')
                printd("Asset hasAudio: %s " % str(asset_found.has_audio))

                asset_found.audio_sources = current_asset.get('audioSources')
                printd("Asset audioSources: %s " % str(asset_found.audio_sources))

                asset_found.audio_channels = current_asset.get('audioChannels')
                printd("Asset audioChannels: %s " % str(asset_found.audio_channels))

                asset_found.audio_rate = current_asset.get('audioRate')
                printd("Asset audioRate: %s " % str(asset_found.audio_rate))

                # Need to store this in a dict properly
                asset_found.metadata = current_asset.find('metadata')
                printd("Asset metadata: %s " % str(asset_found.metadata))

                # Get asset retime percentages
                timeMaps = current_asset.findall('timeMap')
                if timeMaps:
                    for timeMap in timeMaps:
                        timepts = timeMap.findall('timept')
                        if timepts:
                            for timept in timepts:
                                time = get_duration(timept.get('time'))
                                if time != 0:
                                    chunk = (get_duration(timept.get('value')))
                                    percentage = (chunk*100)/time

                    asset_found.percentage = int(round(percentage))

                else:
                    asset_found.percentage = 100

                # -------------------------------------------------------------
                # -------------------------------------------------------------
                # -------------------------------------------------------------
                start = None
                if len(assets) == 1:
                    start = "1"
                    printd("  START:" + str(start))
                else:
                    start = current_asset.get('start')
                    if not start:
                        start = "1"
                        printd("  START: " + str(start))
                    else:
                        start_sec = get_duration(start)
                        sec_per = ((start_sec*asset_found.percentage)/100)
                        asset_found.start_frame = int(sec_per*self.framerate)
                        printd("  START: " +  str(asset_found.start_frame))

                #clip_found.filename = os.path.abspath(clip_found.src)
                duration = current_asset.get('duration')
                full_duration = (get_duration(start) + get_duration(duration))
                full_duration_per = ((full_duration*asset_found.percentage)/100)
                asset_found.end_frame = int(full_duration_per*self.framerate)
                printd("  END: " + str(asset_found.end_frame))

                # -------------------------------------------------------------
                # -------------------------------------------------------------
                # -------------------------------------------------------------

                # Add current clip to the clip list
                self.assets.append(asset_found)

        printd("About to check clips for '{0}'".format(filename))
        if clips:
            self.clip_count = len(clips)
            for current_clip in clips:
                clip_found = clip_wrapper()

                clip_found.name = current_clip.get('name')
                printd("Clip Name: %s " % str(clip_found.name))

                # Get clip percentages
                timeMaps = current_clip.findall('timeMap')
                if timeMaps:
                    for timeMap in timeMaps:
                        timepts = timeMap.findall('timept')
                        if timepts:
                            for timept in timepts:
                                time = get_duration(timept.get('time'))
                                if time != 0:
                                    chunk = (get_duration(timept.get('value')))
                                    percentage = (chunk*100)/time

                    clip_found.percentage = int(round(percentage))

                else:
                    clip_found.percentage = 100

                # -------------------------------------------------------------
                # -------------------------------------------------------------
                # -------------------------------------------------------------
                start = None
                if len(clips) == 1:
                    start = "1"
                    printd("  START", start)
                else:
                    start = current_clip.get('start')
                    if not start:
                        start = "1"
                        printd("  START: " + str(start))
                    else:
                        start_sec = get_duration(start)
                        sec_per = ((start_sec*clip_found.percentage)/100)
                        clip_found.start_frame = int(sec_per*self.framerate)
                        printd("  START: " + str(clip_found.start_frame))

                #clip_found.filename = os.path.abspath(clip_found.src)
                duration = current_clip.get('duration')
                full_duration = (get_duration(start) + get_duration(duration))
                full_duration_per = ((full_duration*clip_found.percentage)/100)
                clip_found.end_frame = int(full_duration_per*self.framerate)
                printd("  END: " + str(clip_found.end_frame))

                # -------------------------------------------------------------
                # -------------------------------------------------------------
                # -------------------------------------------------------------

                # Add current clip to the clip list
                self.clips.append(clip_found)

class clip_wrapper(object):
    """<clip name="Shot0030_720p" offset="0s" duration="69069/24000s" start="106106/24000s" tcFormat="NDF">
        <video offset="106106/24000s" ref="r2" duration="69069/24000s" start="106106/24000s">
            <audio lane="-1" offset="212212/48000s" ref="r2" duration="138138/48000s" start="212212/48000s" role="dialogue" srcCh="1, 2"/>
        </video>
        <keyword start="53053/12000s" duration="69069/24000s" value="mov, shot0030"/>
    </clip>""" 

    def __init__(self):
        self.name = None
        self.percentage = None
        self.start_frame = None
        self.end_frame = None
        self.duration = None

class asset_wrapper(object):
    """<asset id="r4" name="Shot0020_720p" uid="CE3C5DC674DCDF4366D9CEDEECB277CB" src="file:///Shot0020_720p.mov" start="62062/24000s" 
        duration="44044/24000s" hasVideo="1" format="r1" hasAudio="1" audioSources="1" audioChannels="2" audioRate="48000">
        <metadata>
            <md key="com.apple.proapps.spotlight.kMDItemCodecs">
                <array>
                    <string>Apple ProRes 422 LT</string>
                    <string>Linear PCM</string>
                </array>
            </md>
            <md key="com.apple.proapps.mio.ingestDate" value="2015-02-26 09:48:38 +0900"/>
        </metadata>
    </asset>"""

    def __init__(self):
        self.id = None
        self.name = None
        self.uid = None
        self.src = None # In file:// style
        self.percentage = None # Retime percentage       
        self.filepath = None # Full evaluated filename        
        self.start_frame = None
        self.end_frame = None
        self.duration = None
        self.has_video = None
        self.has_audio = None
        self.format = None
        self.audio_sources = None
        self.audio_channels = None
        self.audio_rate = None
        self.metadata = {}