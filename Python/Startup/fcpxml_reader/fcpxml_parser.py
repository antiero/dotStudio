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
        self.library = None
        self.events = []
        self.clips = []
        self.assets = []
        self.speeds = []
        self.projects = []
        self.read_file(filename)

    def getAssetByRefID(self, id):
        for asset in self.assets:
            if asset.id == id:
                return asset        

    def makeClipWrapper(self, clipElement, isSequenceClip = True):
        """Returns a clip_wrapper object from a clipElement"""
        clip_found = clip_wrapper()

        clip_found.name = clipElement.get('name')
        printd("Clip Name: %s " % str(clip_found.name))

        # Get clip percentages
        timeMaps = clipElement.findall('timeMap')
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
        #start = clipElement.get('start')
        start = clipElement.get('offset')
        if not start:
            start = "1"
            printd("  START: " + str(start))
        else:
            start_sec = get_duration(start)
            sec_per = ((start_sec*clip_found.percentage)/100)
            clip_found.start_frame = int(sec_per*self.framerate)
            printd("  START: " + str(clip_found.start_frame))

        #clip_found.filename = os.path.abspath(clip_found.src)
        duration = clipElement.get('duration')
        full_duration = (get_duration(start) + get_duration(duration))
        full_duration_per = ((full_duration*clip_found.percentage)/100)
        clip_found.end_frame = int(full_duration_per*self.framerate)

        # Get the video Track for the Clip, referencing the asset by ref (ref = asset[id])
        video_track = video_track_wrapper()
        videoElement = clipElement.find("video")
        video_track.name = videoElement.get("name")
        offsetString = videoElement.get("offset")
        video_track.offset = get_duration(offsetString)
        durationString = videoElement.get("duration")
        video_track.duration = get_duration(durationString)
        video_track.ref = videoElement.get("ref")
        video_track.role = videoElement.get("role")

        clip_found.video_track = video_track

        clip_found.video_asset = self.getAssetByRefID( clip_found.video_track.ref )

        printd("  END: " + str(clip_found.end_frame))
        printd("file: %s" % clip_found.video_asset.filepath)

        return clip_found       

    def read_file(self, filename):
        percentage = 100

        tree = parse(filename)
        root = tree.getroot()
        resources = root.find('resources')
        printd("Got resources: %s" % str(resources))

        assets = resources.findall('asset')
        printd("Got assets: %s" % str(assets))

        mformat = resources.find('format')

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

        libraryElement = root.find('library') # Appears you can only have one library in fcpxml
        self.library = library_wrapper()
        self.library.location = libraryElement.get("location")
        printd("Got library: %s" % str(libraryElement))

        # This needs to be changed because there can be multiple events in a library
        eventElements = libraryElement.findall('event')        
        printd("Got events: %s" % str(eventElements))

        for eventElement in eventElements:
            current_event = event_wrapper()
            current_event.name = eventElement.get('name')
            current_event.uid = eventElement.get('uid')

            eventClipElements = eventElement.findall('clip')
            for clipElement in eventClipElements:
                clip = self.makeClipWrapper(clipElement)
                current_event.clips.append(clip)

            # Why are we treating this differently?
            projectElements = eventElement.findall('project')
            for projectElement in projectElements:
                current_project = project_wrapper()
                current_project.name = projectElement.get("name")
                current_project.uid = projectElement.get("uid")

                sequenceElement = projectElement.find('sequence')
                current_sequence = sequence_wrapper()
                current_sequence.parentProject = current_project
                durationString = sequenceElement.get("duration")
                current_sequence.duration = get_duration(durationString)
                current_sequence.format = sequenceElement.get("format")
                tcStartString = sequenceElement.get("tcStart")
                current_sequence.timecode_start = get_duration(tcStartString)
                current_sequence.timecode_format = sequenceElement.get("tcFormat")
                current_sequence.audio_layout = sequenceElement.get("audioLayout")
                current_sequence.audio_rate = sequenceElement.get("audioRate")
                current_sequence.name = sequenceElement.get("name")

                spine = sequenceElement.find('spine')
                noteElements = sequenceElement.findall('note')

                # TO-DO: Need to just get the Text from these notes
                current_sequence.notes = noteElements

                sequenceClipElements = (spine.findall('ref-clip') or spine.findall('clip') or
                         spine.findall('video'))
                printd("  sequenceClipElements: " + str(sequenceClipElements))

                for sequenceClipElement in sequenceClipElements:
                    sequenceClip = self.makeClipWrapper(sequenceClipElement)
                    current_sequence.clips.append(sequenceClip)

                current_project.sequences.append(current_sequence)
                self.projects.append(current_project)

            self.events.append(current_event)                
        self.library.events.append(self.events)

        printd("Got projects: %s" % str(self.projects))

class library_wrapper(object):
    """A library contains events and has a location of the fcpbundle
        <library location="file:///Users/ant/Movies/colorway.fcpbundle/">
        <event name="fromPrem" uid="D6D1D992-6E19-4323-9628-BF8E0E430EEF">
    """

    def __init__(self):
        self.location = None
        self.events = []

class event_wrapper(object):
    """An event contains clips and projects (timelines)
            <event name="fromPrem" uid="D6D1D992-6E19-4323-9628-BF8E0E430EEF">
            <clip name="colorway_ref_0001_v1.mov" duration="19/4s" format="r1" tcFormat="NDF">
                <video name="colorway_ref_0001_v1 - v1" offset="0s" ref="r2" duration="19/4s"/>
            </clip>
            <project name="Test2" uid="D3641F16-67D1-4D15-9314-EDA9B89B6AD6">
    """

    def __init__(self):
        self.name = None
        self.uid = None
        self.clips = []
        self.projects = []

class project_wrapper(object):
    """Projects are the highest level items inside an event. They contain the sequences and assets.
    <project name="training_colorway_v1" uid="2E026605-2CD8-4579-9339-0D48401CB3DA">""" 

    def __init__(self):
        self.name = None
        self.uid = None
        self.sequences = []

class sequence_wrapper(object):
    """A sequence (timeline) is nested inside a <project> it has a spine and shots are referred to as clips.
    <sequence duration="1373/24s" format="r1" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">
                    <note>Label 2: Forest</note>
                    <spine>
                        <clip name="colorway-ref-0001-1 " offset="0s" duration="19/4s" tcFormat="NDF">
                            <note>Label 2: Violet</note>
                            <video name="colorway_ref_0001_v1 - v1" offset="0s" ref="r2" duration="19/4s" role="video.V1"/>
                            <clip name="colorway_shotEdit_v1_cut.mp3" lane="-1" offset="1/24s" duration="343/6s" format="r3" tcFormat="DF">
                                <note>Label 2: Caribbean</note>
                                <audio name="colorway_shotEdit_v1_cut - Stereo" offset="0s" ref="r4" duration="6763757/30000s" role="Audio.A1"/>
                                <audio-source srcCh="1, 2" outCh="L, R"/>
                            </clip>
                        </clip>
                        <clip name="colorway-ref-0002-1 " offset="19/4s" duration="1079/24s" tcFormat="NDF">
                            <note>Label 2: Violet</note>
                            <video name="colorway_ref_0002_v1 - v1" offset="0s" ref="r5" duration="1079/24s" role="video.V1"/>
                        </clip>
                        <clip name="colorway-ref-0003-1 " offset="1193/24s" duration="15/2s" tcFormat="NDF">
                            <note>Label 2: Violet</note>
                            <video name="colorway_ref_0003_v1 - v1" offset="0s" ref="r6" duration="15/2s" role="video.V1"/>
                        </clip>
                    </spine>
    </sequence>""" 

    def __init__(self):
        self.parentProject = None
        self.framerate = None
        self.timecode_start = None
        self.timecode_format = None
        self.audio_layout = None
        self.audio_rate = None
        self.duration = None
        self.format = None
        self.notes = []
        self.spines = [] # Can there be multiple spines?...
        self.clips = []

class clip_wrapper(object):
    """A clip contains video and audio tracks and references an asset.
    clips can live inside of events (in the project) or a sequence spine.
    <clip name="Shot0030_720p" offset="0s" duration="69069/24000s" start="106106/24000s" tcFormat="NDF">
        <video offset="106106/24000s" ref="r2" duration="69069/24000s" start="106106/24000s">
            <audio lane="-1" offset="212212/48000s" ref="r2" duration="138138/48000s" start="212212/48000s" role="dialogue" srcCh="1, 2"/>
        </video>
        <keyword start="53053/12000s" duration="69069/24000s" value="mov, shot0030"/>
    </clip>""" 

    def __init__(self):
        self.name = None
        self.percentage = None
        self.timecode_format = None
        self.format = None
        self.video_track = []
        self.audio_track = []
        self.video_asset = None # This will be an asset_wrapper object, in order to get to the MediaSource
        self.start_frame = None
        self.end_frame = None
        self.duration = None

class video_track_wrapper(object):
    """A video track defines a track of video, including duration, timeline offset  
        <video name="colorway_ref_0002_v1 - v1" offset="0s" ref="r3" duration="1079/24s"/>
    """ 

    def __init__(self):
        self.name = None
        self.offset = None #0s
        self.ref = None # This refers to the asset ID?
        self.duration = None #15/2s

class audio_track_wrapper(object):
    """An audio track defines a track of audio, including duration, timeline offset and dialogue info, 
    <audio name="colorway_shotEdit_v1_cut - Stereo" offset="0s" ref="r6" duration="6763757/30000s" role="dialogue">
            <audio name="colorway_shotEdit_v1_cut - Stereo" lane="-1" offset="0s" ref="r6" srcID="2" duration="6763757/30000s" role="dialogue"/>
    </audio>
    """ 

    def __init__(self):
        self.name = None
        self.offset = None #0s
        self.ref = None # This refers to the asset ID?
        self.srcID = None
        self.duration = None #15/2s
        self.role = None # "dialogue", other roles?


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