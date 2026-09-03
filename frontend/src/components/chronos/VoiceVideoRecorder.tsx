"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Mic,
  Video,
  FileText,
  Upload,
  Square,
  Send,
  MessageSquare,
  CheckCircle2,
  AlertCircle,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { chronosApi, EngineResponse, TemporalThread } from "@/lib/chronosApi";

/** Upper bound on a single engine request. If no response arrives in time,
 *  thinking ends and control returns to the user (they can retry). */
const SUBMIT_TIMEOUT_MS = 60_000;

interface VoiceVideoRecorderProps {
  onResponseReceived: (response: EngineResponse) => void;
  onThinkingStart?: () => void;
  onThinkingEnd?: () => void;
  userId?: string;
  activeThread?: TemporalThread | null;
  /** Initial input mode. Defaults to "audio" (existing behavior); first-use
   * experience passes "text" so the clearest interaction is primary. */
  defaultTab?: "text" | "audio" | "video" | "upload";
  /** External prompt to inject into the text input (e.g. from a starter
   * suggestion). When set, the recorder switches to text mode and fills it. */
  injectedPrompt?: string | null;
  /** Called after an injected prompt has been consumed so the parent can
   * clear it and avoid re-filling. */
  onInjectedPromptConsumed?: () => void;
}

export function VoiceVideoRecorder({
  onResponseReceived,
  onThinkingStart,
  onThinkingEnd,
  userId = "user_default",
  activeThread,
  defaultTab = "audio",
  injectedPrompt,
  onInjectedPromptConsumed,
}: VoiceVideoRecorderProps) {
  const [activeTab, setActiveTab] = useState<"text" | "audio" | "video" | "upload">(defaultTab);
  const [textContent, setTextContent] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Audio recording state
  const [isRecordingAudio, setIsRecordingAudio] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioDuration, setAudioDuration] = useState(0);
  const mediaRecorderAudioRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioTimerRef = useRef<any>(null);

  // Video recording state
  const [isRecordingVideo, setIsRecordingVideo] = useState(false);
  const [videoBlob, setVideoBlob] = useState<Blob | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoDuration, setVideoDuration] = useState(0);
  const videoLiveRef = useRef<HTMLVideoElement | null>(null);
  const mediaRecorderVideoRef = useRef<MediaRecorder | null>(null);
  const videoChunksRef = useRef<Blob[]>([]);
  const videoStreamRef = useRef<MediaStream | null>(null);
  const videoTimerRef = useRef<any>(null);

  // File upload state
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  // Unmount guard: prevent setState calls after component unmounts
  const isMountedRef = useRef(true);
  // Abort the in-flight engine request on unmount / retry so thinking never
  // gets stuck and no stale response is applied.
  const submitAbortRef = useRef<AbortController | null>(null);
  // Keep the latest callbacks so cleanup always ends thinking on unmount even
  // if the component is torn down mid-request (avoids a stuck "thinking" feed
  // when the user leaves the conversation while ChronOS is still responding).
  const onThinkingEndRef = useRef(onThinkingEnd);
  useEffect(() => {
    onThinkingEndRef.current = onThinkingEnd;
  }, [onThinkingEnd]);

  // Object URL lifecycle: revoke whichever URL each effect currently captures.
  // Re-running whenever the URL changes revokes the previous preview, and the
  // final cleanup revokes the last one on unmount — so media never lingers.
  useEffect(() => {
    const url = audioUrl;
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [audioUrl]);

  useEffect(() => {
    const url = videoUrl;
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [videoUrl]);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      submitAbortRef.current?.abort();
      // If a request was in flight when we tore down, make sure the parent's
      // "thinking" state is cleared so it can never get stuck.
      onThinkingEndRef.current?.();
      if (audioTimerRef.current) clearInterval(audioTimerRef.current);
      if (videoTimerRef.current) clearInterval(videoTimerRef.current);
      stopVideoCamera();
    };
  }, []);

  // Consume an externally supplied starter prompt — switch to text and fill it.
  useEffect(() => {
    if (injectedPrompt != null && injectedPrompt.trim()) {
      setActiveTab("text");
      setTextContent(injectedPrompt);
      onInjectedPromptConsumed?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [injectedPrompt]);

  const stopVideoCamera = () => {
    if (videoStreamRef.current) {
      videoStreamRef.current.getTracks().forEach((t) => t.stop());
      videoStreamRef.current = null;
    }
  };

  const startAudioRecording = async () => {
    setError(null);
    setAudioBlob(null);
    setAudioUrl(null);
    setAudioDuration(0);
    audioChunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderAudioRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        setAudioBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
        stream.getTracks().forEach((t) => t.stop());
      };

      recorder.start();
      setIsRecordingAudio(true);

      audioTimerRef.current = setInterval(() => {
        setAudioDuration((d) => d + 1);
      }, 1000);
    } catch (err: any) {
      setError("ChronOS couldn't reach your microphone. Please check your browser's permission settings and try again.");
    }
  };

  const stopAudioRecording = () => {
    if (mediaRecorderAudioRef.current && isRecordingAudio) {
      mediaRecorderAudioRef.current.stop();
      setIsRecordingAudio(false);
      if (audioTimerRef.current) clearInterval(audioTimerRef.current);
    }
  };

  const startVideoRecording = async () => {
    setError(null);
    setVideoBlob(null);
    setVideoUrl(null);
    setVideoDuration(0);
    videoChunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      videoStreamRef.current = stream;

      if (videoLiveRef.current) {
        videoLiveRef.current.srcObject = stream;
        videoLiveRef.current.play();
      }

      const recorder = new MediaRecorder(stream);
      mediaRecorderVideoRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) videoChunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(videoChunksRef.current, { type: "video/webm" });
        setVideoBlob(blob);
        setVideoUrl(URL.createObjectURL(blob));
        stopVideoCamera();
      };

      recorder.start();
      setIsRecordingVideo(true);

      videoTimerRef.current = setInterval(() => {
        setVideoDuration((d) => d + 1);
      }, 1000);
    } catch (err: any) {
      setError("ChronOS couldn't reach your camera or microphone. Please check your browser's permission settings and try again.");
    }
  };

  const stopVideoRecording = () => {
    if (mediaRecorderVideoRef.current && isRecordingVideo) {
      mediaRecorderVideoRef.current.stop();
      setIsRecordingVideo(false);
      if (videoTimerRef.current) clearInterval(videoTimerRef.current);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setUploadedFile(file);
    }
  };

  const handleSubmit = async () => {
    if (isProcessing) return;
    setIsProcessing(true);
    setError(null);
    onThinkingStart?.();

    // Abort any previous in-flight request so a stale response can never
    // overwrite the latest one (request sequencing), then start fresh.
    const controller = new AbortController();
    submitAbortRef.current?.abort();
    submitAbortRef.current = controller;

    // Timeout so a hung request always returns control and ends "thinking".
    const timer = setTimeout(() => controller.abort(), SUBMIT_TIMEOUT_MS);

    try {
      const formData = new FormData();
      formData.append("user_id", userId);
      formData.append("provider_key", "chronos");
      formData.append("model_name", "chronos-v1-core");

      if (activeThread) {
        formData.append("active_thread_id", activeThread.id);
      }

      if (activeTab === "text") {
        if (!textContent.trim()) {
          throw new Error("Please write something first.");
        }
        formData.append("content", textContent);
        formData.append("input_type", "text");
      } else if (activeTab === "audio") {
        if (!audioBlob) {
          throw new Error("Please record a voice note first.");
        }
        formData.append("file", audioBlob, `voice_recording_${Date.now()}.webm`);
        formData.append("input_type", "audio");
        formData.append("content", textContent.trim());
      } else if (activeTab === "video") {
        if (!videoBlob) {
          throw new Error("Please record a video note first.");
        }
        formData.append("file", videoBlob, `video_recording_${Date.now()}.webm`);
        formData.append("input_type", "video");
        formData.append("content", textContent.trim());
      } else if (activeTab === "upload") {
        if (!uploadedFile) {
          throw new Error("Please choose a file to upload.");
        }
        formData.append("file", uploadedFile);
        let type = "text";
        if (uploadedFile.type.includes("audio")) type = "audio";
        else if (uploadedFile.type.includes("video")) type = "video";
        formData.append("input_type", type);
        formData.append("content", textContent || `Uploaded media: ${uploadedFile.name}`);
      }

      const response = await chronosApi.processInput(formData, controller.signal);
      if (!isMountedRef.current) return;
      onResponseReceived(response);

      setTextContent("");
      setAudioBlob(null);
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
      setAudioDuration(0);
      setVideoBlob(null);
      if (videoUrl) URL.revokeObjectURL(videoUrl);
      setVideoUrl(null);
      setVideoDuration(0);
      setUploadedFile(null);
      onThinkingEnd?.();
    } catch (err: any) {
      if (!isMountedRef.current) return;
      // Guard against leaking raw provider/network details to the user.
      const isUserValidation =
        err?.message === "Please write something first." ||
        err?.message === "Please record a voice note first." ||
        err?.message === "Please record a video note first." ||
        err?.message === "Please choose a file to upload.";
      const message = isUserValidation
        ? err.message
        : controller.signal.aborted
          ? "That took too long. Please try again."
          : "Something went wrong while processing that. Please try again.";
      setError(message);
      onThinkingEnd?.();
    } finally {
      clearTimeout(timer);
      if (submitAbortRef.current === controller) submitAbortRef.current = null;
      if (isMountedRef.current) setIsProcessing(false);
    }
  };

  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  const modeTabs = [
    { key: "audio" as const, label: "Voice", icon: Mic },
    { key: "video" as const, label: "Video", icon: Video },
    { key: "text" as const, label: "Text", icon: FileText },
    { key: "upload" as const, label: "File", icon: Upload },
  ];

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-6 sm:p-7">
        {/* Header */}
        <div className="mb-6 flex items-center gap-3 border-b border-border/60 pb-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-accent-foreground">
            <MessageSquare className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-[15px] font-semibold">Talk to ChronOS</h3>
            <p className="text-xs text-muted">A voice note, a video, or a few words — how you&apos;re feeling right now</p>
          </div>
        </div>

        {/* Mode tabs */}
        <div className="mb-6 grid grid-cols-4 gap-1 rounded-xl bg-secondary/50 p-1">
          {modeTabs.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              aria-pressed={activeTab === key}
              className={`flex items-center justify-center gap-2 rounded-lg py-2 text-xs font-medium transition-all duration-200 ${
                activeTab === key
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted hover:text-foreground"
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </div>

        {/* TAB 1: RECORD VOICE */}
        {activeTab === "audio" && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            {!isRecordingAudio && !audioUrl && (
              <button
                onClick={startAudioRecording}
                className="group flex h-20 w-20 items-center justify-center rounded-full border border-border bg-secondary transition-all duration-200 hover:scale-105 hover:bg-secondary/70 active:scale-95"
              >
                <Mic className="h-8 w-8 text-accent-foreground" />
                <span className="sr-only">Record voice</span>
              </button>
            )}

            {isRecordingAudio && (
              <div className="flex flex-col items-center gap-5">
                <div className="relative flex h-24 w-24 items-center justify-center">
                  <span className="absolute h-full w-full animate-ping rounded-full bg-rose-500/20 motion-reduce:animate-none" />
                  <button
                    onClick={stopAudioRecording}
                    className="relative z-10 flex h-16 w-16 items-center justify-center rounded-full bg-rose-600 text-white transition-transform hover:scale-105 active:scale-95"
                    aria-label="Stop recording"
                  >
                    <Square className="h-6 w-6 fill-current" />
                  </button>
                </div>
                <div>
                  <p role="status" className="text-sm font-medium text-rose-400/90">Recording</p>
                  <p className="mt-1 text-2xl font-semibold tabular-nums">{formatTime(audioDuration)}</p>
                </div>
              </div>
            )}

            {audioUrl && !isRecordingAudio && (
              <div className="flex w-full max-w-md flex-col items-center gap-3">
                <div className="flex w-full items-center gap-3 rounded-xl border border-border bg-secondary/30 p-3">
                  <Mic className="h-5 w-5 shrink-0 text-accent-foreground" />
                  <audio src={audioUrl} controls className="h-8 w-full min-w-0" />
                  <button
                    onClick={() => {
                      if (audioUrl) URL.revokeObjectURL(audioUrl);
                      setAudioUrl(null);
                      setAudioBlob(null);
                    }}
                    className="text-muted transition-colors hover:text-foreground"
                    aria-label="Discard recording"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <p role="status" className="flex items-center gap-1.5 text-xs text-emerald-400/90">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Recorded {formatTime(audioDuration)}
                </p>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: RECORD VIDEO */}
        {activeTab === "video" && (
          <div className="flex flex-col items-center justify-center py-6 text-center">
            {!isRecordingVideo && !videoUrl && (
              <button
                onClick={startVideoRecording}
                className="group flex h-20 w-20 items-center justify-center rounded-full border border-border bg-secondary transition-all duration-200 hover:scale-105 hover:bg-secondary/70 active:scale-95"
              >
                <Video className="h-8 w-8 text-accent-foreground" />
                <span className="sr-only">Record video</span>
              </button>
            )}

            {isRecordingVideo && (
              <div className="flex w-full max-w-md flex-col items-center gap-4">
                <div className="relative aspect-video w-full overflow-hidden rounded-xl border border-border bg-black">
                  <video ref={videoLiveRef} muted className="h-full w-full object-cover" />
                  <div className="absolute left-3 top-3 flex items-center gap-2 rounded-full bg-black/60 px-3 py-1 text-xs font-medium text-rose-400 backdrop-blur">
                    REC {formatTime(videoDuration)}
                  </div>
                </div>
                <Button variant="destructive" onClick={stopVideoRecording} className="gap-2">
                  <Square className="h-4 w-4 fill-current" /> Stop recording
                </Button>
              </div>
            )}

            {videoUrl && !isRecordingVideo && (
              <div className="flex w-full max-w-md flex-col items-center gap-3">
                <div className="relative aspect-video w-full overflow-hidden rounded-xl border border-border bg-black">
                  <video src={videoUrl} controls className="h-full w-full object-cover" />
                </div>
                <div className="flex items-center gap-3">
                  <p role="status" className="flex items-center gap-1.5 text-xs text-emerald-400/90">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Captured {formatTime(videoDuration)}
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      if (videoUrl) URL.revokeObjectURL(videoUrl);
                      setVideoUrl(null);
                      setVideoBlob(null);
                    }}
                  >
                    Retake
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: TEXT MEMORY */}
        {activeTab === "text" && (
          <div className="py-2">
            <textarea
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              placeholder="What's on your mind?"
              aria-label="What's on your mind?"
              className="h-32 w-full resize-none rounded-xl border border-border bg-secondary/30 p-4 text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
        )}

        {/* TAB 4: FILE UPLOAD */}
        {activeTab === "upload" && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-secondary/20 p-8 text-center">
            <Upload className="mb-3 h-7 w-7 text-muted" />
            <p className="text-sm font-medium">Upload a voice note, video, or document</p>
            <p className="mt-1 text-xs text-muted">MP3, WAV, MP4, WEBM, M4A, TXT</p>
            <input
              type="file"
              onChange={handleFileUpload}
              accept="audio/*,video/*,text/*"
              className="mt-4 cursor-pointer text-xs text-muted file:mr-3 file:rounded-lg file:border-0 file:bg-primary file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-primary-foreground"
            />
            {uploadedFile && (
              <p role="status" className="mt-3 flex items-center gap-1.5 text-xs text-emerald-400/90">
                <CheckCircle2 className="h-3.5 w-3.5" /> Selected {uploadedFile.name} ({(uploadedFile.size / 1024).toFixed(1)} KB)
              </p>
            )}
          </div>
        )}

        {activeTab !== "text" && (
          <div className="mt-4">
            <input
              type="text"
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              placeholder="Optional note to go with this memory..."
              aria-label="Optional note to go with this memory"
              className="w-full rounded-lg border border-border bg-secondary/30 px-3 py-2 text-xs text-foreground placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
        )}

        {error && (
          <div role="alert" className="mt-4 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="mt-6 flex items-center justify-end gap-3 border-t border-border/60 pt-5">
          <Button
            onClick={handleSubmit}
            disabled={isProcessing}
            className="gap-2 bg-primary px-5 text-primary-foreground"
          >
            {isProcessing ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent motion-reduce:animate-none" />
                Sending...
              </>
            ) : (
              <>
                <Send className="h-3.5 w-3.5" /> Send
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}