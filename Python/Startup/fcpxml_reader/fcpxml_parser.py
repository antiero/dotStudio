from __future__ import division
from xml.etree.ElementTree import parse, Element
from fcpxml_definitions import *
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
        self.formats = []        
        self.read_file(filename)

    def getAssetByRefID(self, id):
        """Returns a asset_wrapper object based on its ID"""
        for asset in self.assets:
            if asset.id == id:
                return asset

    def getFormatByFormatID(self, id):
        """Returns a format_wrapper object based on its ID"""
        for format in self.formats:
            if format.id == id:
                return format

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
            printd("SEQ CLIP START: " + str(clip_found.start_frame))

        #clip_found.filename = os.path.abspath(clip_found.src)
        duration = clipElement.get('duration')
        full_duration = (get_duration(start) + get_duration(duration))
        full_duration_per = ((full_duration*clip_found.percentage)/100)
        clip_found.end_frame = int(full_duration_per*self.framerate)

        # Get the video Track for the Clip, referencing the asset by ref (ref = asset[id])
        
        videoElement = clipElement.find("video") # Should maybe be a findall?

        if isinstance(videoElement, Element):
            printd("Got videoElement")
            video_track = video_track_wrapper()
            video_track.name = videoElement.get("name")
            offsetString = videoElement.get("offset")
            video_track.offset = get_duration(offsetString)
            durationString = videoElement.get("duration")
            video_track.duration = get_duration(durationString)
            video_track.ref = videoElement.get("ref")
            video_track.role = videoElement.get("role")
            clip_found.video_track = video_track
            clip_found.asset = self.getAssetByRefID( clip_found.video_track.ref )

        audioElement = clipElement.find("audio") # Should maybe be a findall?

        if isinstance(audioElement, Element):
            printd("Got audioElement")
            audio_track = audio_track_wrapper()
            audio_track.name = audioElement.get("name")
            offsetString = audioElement.get("offset")
            audio_track.offset = get_duration(offsetString)
            durationString = audioElement.get("duration")
            audio_track.duration = get_duration(durationString)
            audio_track.ref = audioElement.get("ref")
            audio_track.role = audioElement.get("role")
            clip_found.audio_track = audio_track
            clip_found.asset = self.getAssetByRefID( clip_found.audio_track.ref )

        printd("  END: " + str(clip_found.end_frame))
        if clip_found.asset:
            printd("file: %s" % clip_found.asset.filepath)

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

        masterFormats = resources.findall('format')
        for formatElem in masterFormats:
            format = format_wrapper()
            format.id = formatElem.get("id")
            format.name = formatElem.get("name")
            format.width = formatElem.get("width")
            format.height = formatElem.get("height")
            format.frame_duration = formatElem.get("frameDuration")
            format.frame_rate = timevalue_to_seconds(formatElem.get("frameDuration"))
            self.formats += [format]

        # Get the framerate
        self.framerate = timevalue_to_seconds(mformat.get('frameDuration'))
        printd("**** FPS: %s " % self.framerate)
        #printd("About to check assets for '{0}'".format(filename))
        if assets:
            self.asset_count = len(assets)
            for current_asset in assets:
                asset_found = asset_wrapper()

                # TO-DO: Just tidy this up in a loop with list of needed attributes
                asset_found.id = current_asset.get('id')
                #printd("Asset ID: %s " % str(asset_found.id))

                asset_found.name = current_asset.get('name')
                #printd("Asset Name: %s " % str(asset_found.name))

                asset_found.uid = current_asset.get('uid')
                #printd("Asset UID: %s " % str(asset_found.uid))

                asset_found.src = current_asset.get('src')
                #printd("Asset src: %s " % str(asset_found.src))

                url = urlparse.urlparse(asset_found.src)
                asset_found.filepath = os.path.abspath(os.path.join(url.netloc, url.path))
                #printd("Asset filepath: %s " % str(asset_found.filepath))

                asset_found.has_video = current_asset.get('hasVideo')
                #printd("Asset hasVideo: %s " % str(asset_found.has_video))

                asset_found.format = current_asset.get('format')
                #printd("Asset format: %s " % str(asset_found.format))

                asset_found.has_audio = current_asset.get('hasAudio')
                #printd("Asset hasAudio: %s " % str(asset_found.has_audio))

                asset_found.audio_sources = current_asset.get('audioSources')
                #printd("Asset audioSources: %s " % str(asset_found.audio_sources))

                asset_found.audio_channels = current_asset.get('audioChannels')
                #printd("Asset audioChannels: %s " % str(asset_found.audio_channels))

                asset_found.audio_rate = current_asset.get('audioRate')
                #printd("Asset audioRate: %s " % str(asset_found.audio_rate))

                # Need to store this in a dict properly
                asset_found.metadata = current_asset.find('metadata')
                #printd("Asset metadata: %s " % str(asset_found.metadata))

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
                current_sequence.format = self.getFormatByFormatID(sequenceElement.get("format"))
                current_sequence.width = current_sequence.format.width
                current_sequence.height = current_sequence.format.height
                current_sequence.frame_rate = current_sequence.format.frame_rate
                tcStartString = sequenceElement.get("tcStart")
                current_sequence.timecode_start = get_duration(tcStartString)
                current_sequence.timecode_format = sequenceElement.get("tcFormat")
                current_sequence.audio_layout = sequenceElement.get("audioLayout")
                current_sequence.audio_rate = sequenceElement.get("audioRate")
                current_sequence.name = current_project.name
                

                spine = sequenceElement.find('spine')
                noteElements = sequenceElement.findall('note')

                # TO-DO: Need to just get the Text from these notes
                #current_sequence.notes = noteElements

                sequenceClipElements = spine.findall('clip')
                printd("Current 'Sequence' (project) name is %s\n" % current_sequence.name)
                printd("  sequenceClipElements: " + str(sequenceClipElements))

                for sequenceClipElement in sequenceClipElements:
                    sequenceClip = self.makeClipWrapper(sequenceClipElement)
                    current_sequence.clips.append(sequenceClip)

                current_project.sequences.append(current_sequence)
                self.projects.append(current_project)

            self.events.append(current_event)                
        self.library.events.append(self.events)

        printd("Got projects: %s" % str(self.projects))