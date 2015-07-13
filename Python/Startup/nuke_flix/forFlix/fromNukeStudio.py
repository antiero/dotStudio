import fromFCP
import re
import os
from flix.core2.markerShot import MarkerShot
from flix.utilities.log import log
from flix.toEditorial.fromMovNuke import FromMovNuke
from flix.remote.remoteHttpCall import ProxyHttpCall
from flix.remote.remoteHttpCall import FlixJob
from flix import remote
import flix
from pyamf import remoting

class FromNukeStudio(fromFCP.FromFCP):

    def __init__(self, show, sequence, branch, edlFile, movie, comment, username, importAsStills=True, shotgunPub=False):
        
        fromFCP.FromFCP.__init__(self, show, sequence, branch, edlFile, movie, comment, username, importAsStills=importAsStills, shotgunPub=shotgunPub)
        
        # importAsStills option comes in as a string. Convert to bool...
        importAsStillsBool = True if str(importAsStills) in ['True','true', 'yes', 'YES'] else False
        self.importAsStills = importAsStillsBool

    def breakdownMovie(self):
        """Export out the frames and audio from the movie"""

        frameRanges = []
        for c in self.mergedClips:
            recipe = c.recipe
            if isinstance(recipe, dict):
                frameRanges.append([recipe['refStart'], recipe['refEnd']])

        log('FrameRanges %s' % frameRanges, isInfo=True)

        self.sound = ''
        self.refMovie = ''

        if self.movie != '' and self.movie is not None:
            movFolder = self.mode.get('[editorialMOVFolder]')
            if not self.fileService.exists(os.path.dirname(movFolder)):
                self.fileService.createFolders(os.path.dirname(movFolder))
            tempMov = "%s/%s"%(movFolder, os.path.basename(self.movie))
            self.fileService.copy(self.movie, tempMov)
            self.fromMov = self.remoteExecute(1000, "FromMovNuke.convert", self.show, self.sequence, self.editVersion, tempMov, frameRanges, self.lookupFile)
            if isinstance(self.fromMov, remoting.ErrorFault):
                self.fromMov.raiseException()
            self.verifyRefImages(frameRanges)
            self.sound = self.fromMov['mp3']
            self.refMovie = self.fromMov['mov']

    def remoteExecute(self, deadline, command, *options):
        """
        execute on a remote proc the provided method and options
        """
        proxyHttpCall = ProxyHttpCall()
        procs = remote.ProcConfig()
        maxAttempts = 5
        job = FlixJob('user', 'nuke')
        request = job.newRequest(procs.NUKE, command, *options)
        request.deadline = deadline
        result = proxyHttpCall.makeRequest(request, job, True, maxAttempts)
        return result

    def getRecipePropertiesFromClip(self, clip, name=None):

        if name:
            parts = name.split("_")
        else:
            if clip.name.startswith('_uuid_'):
                return None
            parts = clip.name.split(" ")[0]
            parts = parts.split("-")
        properties = {}

        # todo verify the sequence exists
        log("*** fromNukeStudio: getRecipePropertiesFromClip - clip: %s, name %s, parts: %s" % (str(clip), str(name), str(parts)), isInfo=True)

        if len(parts) == 3:
            # parse the name if the version is missing
            properties["show"] = self.show
            properties["sequence"] = parts[0]
            properties["beat"] = parts[1]
            properties["setup"] = parts[2]
            properties["version"] = "1"
            return properties
        elif len(parts) > 3:
            properties["show"] = self.show
            properties["sequence"] = ''.join(parts[0:-3])
            properties["beat"] = parts[-3]
            properties["setup"] = parts[-2]
            properties["version"] = "1"
            if parts[-1].isdigit():
                properties["version"] = parts[-1]
            return properties

        # Nuke Studio Clip names use underscores for clipitem names
        elif len(parts) == 1:
            clipNameParts = parts[0].split('_') # parts e.g: ['hum', 'p', '1033', 'v2.hd']
            
            # We need four parts of the Clip name... if not it's ref
            if len(clipNameParts) != 4:
                return None

            properties["show"] = self.show
            properties["sequence"] = clipNameParts[0]
            properties["beat"] = clipNameParts[1]
            properties["setup"] = clipNameParts[2]
            properties["version"] = clipNameParts[3].replace('v','').replace('.hd','')
            if not properties["version"].isdigit():
                properties["version"] = "1"
            return properties

        return None

    def parseEDL(self):
        super(FromNukeStudio, self).parseEDL()
        """markerList = []
        for index, clip in enumerate(self.clips):
            markerSetup = getattr(clip, 'markerSetup', None)
            marker = MarkerShot()
            if not markerSetup:
                markerSetup = '%03d'%(int(index)+1)
            markerArgs = {'name':markerSetup,
                          'start':clip.timelineStart}
            marker.conformFromClipItem(markerArgs)
            markerList.append(marker)
        self.clips.extend(markerList)"""

    def emailResult(self):

    # email publish summary
        try:
            publishTemplateName = self.shotCutList.mode[fromFCP.kParamImportTemplate]
            publishSummary      = flix.utilities.template.render(publishTemplateName, **{
                'cutlist'          : self.shotCutList,
                'comment'          : self.comment,
                })
            show = self.shotCutList.show
            sequence = self.shotCutList.sequence

            # grab tracking code for sequence
            trackingCode = flix.core.sequence.Sequence(show, sequence).getTrackingIndex()
            mode = self.shotCutList.mode
            kargs = {}
            # compile subject
            kargs['[trackingCode]']        = (" %s" % trackingCode).rstrip()
            kargs['[sequenceInfo]']        = "[show]/[sequence][trackingCode]"
            kargs['[emailSubjectMessage]'] = "From Nuke Studio [sequenceInfo]"
            kargs['[emailSubjectComment]'] = self.comment

            # email summary
            log("Nuke Studio: Emailing Publish Summary: %s" % kargs)
            with mode.using(kargs):
                flix.utilities.email.sendHtmlEmail(
                    '[FLIX_USER]@[domain]', '[emailFromEditorial]',
                    '[emailFullSubject]', publishSummary, mode)

        # email error to support
        except Exception, e:
            log('Publish email summary failed.%s' % e, trace=True, isError=True)
        return