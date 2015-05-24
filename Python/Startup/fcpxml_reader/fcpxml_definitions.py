# Contains the object wrapper definitions for fcp xml elements

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

class format_wrapper(object):
    """Formats are contained in the resources element, containing info about the clip/sequence format
    <format id="r1" name="FFVideoFormat720p2398" frameDuration="1001/24000s" width="1280" height="720"/>
    """ 
    def __init__(self):
        self.name = None
        self.id = None # r1
        self.width = None
        self.height = None
        self.framerate = None # 25
        self.frame_duration = None # 25

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
        self.format = None        
        self.framerate = None
        self.width = None
        self.height = None
        self.timecode_start = None
        self.timecode_format = None
        self.audio_layout = None
        self.audio_rate = None
        self.duration = None
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
        self.framerate = None
        self.video_track = []
        self.audio_track = []
        self.asset = None # This will be an asset_wrapper object, in order to get to the MediaSource
        self.start_frame = None
        self.end_frame = None
        self.duration = None

        self.lane = 0 # The lane is akin to a Video track, an integer offset from 0, being the default video track

        # Clips are not treated specially like TrackItems in NS.
        # Debating whether to include a trackitem_wrapper, with a clip_wrapper as source
        self.timeline_in = None
        self.timeline_out = None

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