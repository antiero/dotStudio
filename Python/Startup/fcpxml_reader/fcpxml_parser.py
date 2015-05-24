from __future__ import division
from xml.etree.ElementTree import parse, Element
from fcpxml_definitions import *
import os, urlparse

debug = True
def printd(str):
    global debug
    if debug:
        print(str)

def timestringToSecs(time_str):
    """Converts time strings (351/25s) into a time value in seconds (14.04)"""
    time_str = time_str.replace('s','')
    time_float = eval('float(%s)' % time_str)
    return time_float

def get_frames_from_time(seconds, fps):
    ''' Returns the numer of frames in the amount of
    seconds specified using the framerate specified.

    '''
    return int(seconds * fps)

class fcpxml_wrapper(object):
    def __init__(self, filename = None):
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

        if filename:        
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

    def makeClipWrapper(self, clipElement, parentSequence = None, isSubClip = False, isSequenceClip = False):
        """Returns a clip_wrapper object from a clipElement
        It providing a parent Sequence, the returned object should provide a trackitem_wrapper?
        'isSubClip' is True if the Clip is nested, we use this to work out the offset (maybe)
        'isSequenceClip' is True if the Clip is in a Sequence (like a TrackItem)
        """
        clip_found = clip_wrapper()
        clip_found.name = clipElement.get('name')

        # Add the lane (track index) if the Clip is a subclip..
        if isSubClip:
            clip_found.lane = int(clipElement.get('lane'))

        # A clip optionally specified a format if its a Sequence Clip.
        formatElement = clipElement.get('format')
        if formatElement:
            clip_found.format = self.getFormatByFormatID(formatElement)
            clip_found.framerate = clip_found.format.framerate

        # Get the video Track for the Clip, referencing the asset by ref (ref = asset[id])
        videoElement = clipElement.find("video") # Should maybe be a findall?

        if isinstance(videoElement, Element):
            #printd("Got videoElement")
            video_track = video_track_wrapper()
            video_track.name = videoElement.get("name")
            offsetString = videoElement.get("offset")
            video_track.offset = timestringToSecs(offsetString)
            durationString = videoElement.get("duration")
            video_track.duration = timestringToSecs(durationString)
            video_track.ref = videoElement.get("ref")
            video_track.role = videoElement.get("role")
            clip_found.video_track = video_track
            clip_found.asset = self.getAssetByRefID( clip_found.video_track.ref )

            # Get the frame rate from the asset...
            #clip_found.framerate = clip_found.asset.framerate

        audioElement = clipElement.find("audio") # Should maybe be a findall?

        if isinstance(audioElement, Element):
            #printd("Got audioElement")
            audio_track = audio_track_wrapper()
            audio_track.name = audioElement.get("name")
            offsetString = audioElement.get("offset")
            audio_track.offset = timestringToSecs(offsetString)
            durationString = audioElement.get("duration")
            audio_track.duration = timestringToSecs(durationString)
            audio_track.ref = audioElement.get("ref")
            audio_track.role = audioElement.get("role")
            clip_found.audio_track = audio_track
            clip_found.asset = self.getAssetByRefID( clip_found.audio_track.ref )        

        # Get clip percentages
        timeMaps = clipElement.findall('timeMap')
        if timeMaps:
            for timeMap in timeMaps:
                timepts = timeMap.findall('timept')
                if timepts:
                    for timept in timepts:
                        time = timestringToSecs(timept.get('time'))
                        if time != 0:
                            chunk = (timestringToSecs(timept.get('value')))
                            percentage = (chunk*100)/time

            clip_found.percentage = int(round(percentage))

        else:
            clip_found.percentage = 100

        # -------------------------------------------------------------
        # -------------------------------------------------------------
        # -------------------------------------------------------------

        # We now need to work out the source in and source out for Clips...
        start = clipElement.get('start')

        # A <clip> in a sequence does not have to have a start attribute
        # If no start exists, the source frame is assumed to be 0.
        if not start:
            start = "0s"

        if not clip_found.framerate:
            # FUGLY - FIX THIS!
            clip_found.framerate = self.getFormatByFormatID(clip_found.asset.format).framerate

        printd("Got Clip with framerate: %s" % str(clip_found.framerate))

        start_sec = timestringToSecs(start)
        printd("Got start element %s, which is %s secs" % (str(start), str(start_sec)))
        #sec_per = ((start_sec*clip_found.percentage)/100)
        #printd("parentSequence framerate: " + str(parentSequence.framerate))
        clip_found.start_frame = int(start_sec*clip_found.framerate)
        printd("SEQ CLIP SOURCE START: " + str(clip_found.start_frame))

        # SOURCE OUT
        #clip_found.filename = os.path.abspath(clip_found.src)
        duration = clipElement.get('duration')
        duration_sec = timestringToSecs(duration)
        #duration_retimed = ((duration_sec*clip_found.percentage)/100)

        # Need to confirm it's correct to use parent Sequence framerate here...
        if parentSequence:
            duration_frames = int(duration_sec*parentSequence.framerate)
        else:
            duration_frames = int(duration_sec*clip_found.framerate)

        printd("SEQ CLIP DURATION: " + str(duration_frames))
        printd("SEQ CLIP SOURCE END: " + str(clip_found.start_frame+duration_frames-1))        
        clip_found.end_frame = clip_found.start_frame+duration_frames-1

        # If the Clip is in a Sequence, we also care about its position in the timeline...
        if isSequenceClip:
            timeline_offset = clipElement.get('offset')
            timeline_offset_sec = timestringToSecs(timeline_offset)
            timeline_offset_frame = int(timeline_offset_sec * parentSequence.framerate)
            printd("TIMELINE CUT IN FRAME: " + str(timeline_offset_frame))
            clip_found.timeline_in = timeline_offset_frame

            timeline_out = (timeline_offset_frame + duration_frames) - 1
            clip_found.timeline_out = timeline_out
            printd("TIMELINE CUT OUT FRAME: " + str(timeline_out))

        return clip_found       

    def read_file(self, filename):
        percentage = 100

        tree = parse(filename)
        root = tree.getroot()
        resources = root.find('resources')
        #printd("Got resources: %s" % str(resources))

        assets = resources.findall('asset')
        #printd("Got assets: %s" % str(assets))

        mformat = resources.find('format')

        masterFormats = resources.findall('format')
        for formatElem in masterFormats:
            format = format_wrapper()
            format.id = formatElem.get("id")
            format.name = formatElem.get("name")
            format.width = formatElem.get("width")
            format.height = formatElem.get("height")
            format.frame_duration = formatElem.get("frameDuration")
            format.framerate = 1.0 / timestringToSecs(formatElem.get("frameDuration"))
            self.formats += [format]

        # Get the framerate - this needs to be done PER Clip, based on the format!
        self.framerate = 1.0 / timestringToSecs(mformat.get('frameDuration'))
        #printd("**** FPS: %s " % self.framerate)
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
                                time = timestringToSecs(timept.get('time'))
                                if time != 0:
                                    chunk = (timestringToSecs(timept.get('value')))
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
                    #printd("  START:" + str(start))
                else:
                    start = current_asset.get('start')
                    if not start:
                        start = "1"
                        #printd("  START: " + str(start))                    
                    else:
                        start_sec = timestringToSecs(start)
                        sec_per = ((start_sec*asset_found.percentage)/100)
                        asset_found.start_frame = int(sec_per*self.framerate)
                        #printd("  START: " +  str(asset_found.start_frame))

                #clip_found.filename = os.path.abspath(clip_found.src)
                duration = current_asset.get('duration')
                full_duration = (timestringToSecs(start) + timestringToSecs(duration))
                full_duration_per = ((full_duration*asset_found.percentage)/100)
                asset_found.end_frame = int(full_duration_per*self.framerate)
                #printd("  END: " + str(asset_found.end_frame))

                # -------------------------------------------------------------
                # -------------------------------------------------------------
                # -------------------------------------------------------------

                # Add current clip to the clip list
                self.assets.append(asset_found)        

        libraryElement = root.find('library') # Appears you can only have one library in fcpxml
        self.library = library_wrapper()
        self.library.location = libraryElement.get("location")
        #printd("Got library: %s" % str(libraryElement))

        # This needs to be changed because there can be multiple events in a library
        eventElements = libraryElement.findall('event')        
        #printd("Got events: %s" % str(eventElements))

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
                current_sequence.duration = timestringToSecs(durationString)
                current_sequence.format = self.getFormatByFormatID(sequenceElement.get("format"))
                current_sequence.width = current_sequence.format.width
                current_sequence.height = current_sequence.format.height
                current_sequence.framerate = current_sequence.format.framerate
                tcStartString = sequenceElement.get("tcStart")
                current_sequence.timecode_start = timestringToSecs(tcStartString)
                current_sequence.timecode_format = sequenceElement.get("tcFormat")
                current_sequence.audio_layout = sequenceElement.get("audioLayout")
                current_sequence.audio_rate = sequenceElement.get("audioRate")
                current_sequence.name = current_project.name
                

                spine = sequenceElement.find('spine')
                noteElements = sequenceElement.findall('note')

                # TO-DO: Need to just get the Text from these notes
                #current_sequence.notes = noteElements

                sequenceClipElements = spine.findall('clip')
                #printd("Current 'Sequence' (project) name is %s\n" % current_sequence.name)
                #printd("  sequenceClipElements: " + str(sequenceClipElements))

                for sequenceClipElement in sequenceClipElements:

                    sequenceClip = self.makeClipWrapper(sequenceClipElement, parentSequence=current_sequence, isSequenceClip=True)
                    current_sequence.clips.append(sequenceClip)

                    # We need to also traverse the clip elements to find any sub-clips...
                    # Q) Can this sub-clip be more than 1 level deep... I'm sure it could be...
                    subclips = sequenceClipElement.findall('clip')
                    if len(subclips)==0:
                        printd("No Sub-Clips found - hooray!")                    
                    else:
                        printd("*** %i Sub-<clip> elements found!" % (len(subclips)))
                        for subclipElement in subclips:
                            sequenceClip = self.makeClipWrapper(subclipElement, parentSequence=current_sequence, isSubClip=True, isSequenceClip=True)
                            current_sequence.clips.append(sequenceClip)

                current_project.sequences.append(current_sequence)
                self.projects.append(current_project)

            self.events.append(current_event)                
        self.library.events.append(self.events)

        #printd("Got projects: %s" % str(self.projects))