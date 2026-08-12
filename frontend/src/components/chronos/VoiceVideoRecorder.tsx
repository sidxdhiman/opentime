"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Mic,
  Video,
  FileText,
  Upload,
  Square,
  Sparkles,
  Send,
  Cpu,
  CheckCircle2,
  AlertCircle,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { chronosApi, EngineResponse } from "@/lib/chronosApi";

interface VoiceVideoRecorderProps {
  onResponseReceived: (response: EngineResponse) => void;
  userId?: string;
}

export function VoiceVideoRecorder({
  onResponseReceived,
  userId = "user_default",
}: VoiceVideoRecorderProps) {
  const [activeTab, setActiveTab] = useState<"text" | "audio" | "video" | "upload">("audio");
  const [textContent, setTextContent] = useState("");
  const [selectedProvider, setSelectedProvider] = useState("chronos");
  const [selectedModel, setSelectedModel] = useState("chronos-v1-core");
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

  const providersList = [
    { key: "chronos", name: "ChronOS Core", model: "chronos-v1-core", badge: "Engine" },
    { key: "openai", name: "OpenAI GPT-4o", model: "gpt-4o", badge: "Cloud" },
    { key: "anthropic", name: "Claude Sonnet", model: "claude-3-5-sonnet", badge: "Cloud" },
    { key: "gemini", name: "Google Gemini", model: "gemini-1.5-pro", badge: "Cloud" },
    { key: "ollama", name: "Ollama Local", model: "llama3:latest", badge: "Local" },
  ];

  useEffect(() => {
    return () => {
      if (audioTimerRef.current) clearInterval(audioTimerRef.current);
      if (videoTimerRef.current) clearInterval(videoTimerRef.current);
      stopVideoCamera();
    };
  }, []);

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
      setError("Microphone access denied or unavailable: " + (err.message || err));
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
      setError("Camera/Microphone access denied or unavailable: " + (err.message || err));
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
    setIsProcessing(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("user_id", userId);
      formData.append("provider_key", selectedProvider);
      formData.append("model_name", selectedModel);

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

      const response = await chronosApi.processInput(formData);
      onResponseReceived(response);

      setTextContent("");
      setAudioBlob(null);
      setAudioUrl(null);
      setAudioDuration(0);
      setVideoBlob(null);
      setVideoUrl(null);
      setVideoDuration(0);
      setUploadedFile(null);
    } catch (err: any) {
      setError(err.message || "Failed to process input through ChronOS Engine");
    } finally {
      setIsProcessing(false);
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
        <div className="mb-6 flex flex-col gap-4 border-b border-border/60 pb-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-accent-foreground">
              <Cpu className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h3 className="text-[15px] font-semibold">Share a moment</h3>
                <span className="rounded-full border border-border bg-secondary/40 px-2 py-0.5 text-[11px] font-medium text-muted">
                  Model-agnostic
                </span>
              </div>
              <p className="text-xs text-muted">Voice, video, text, or a file — ChronOS listens</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-muted">Engine</span>
            <select
              value={selectedProvider}
              onChange={(e) => {
                const provKey = e.target.value;
                setSelectedProvider(provKey);
                const found = providersList.find((p) => p.key === provKey);
                if (found) setSelectedModel(found.model);
              }}
              className="rounded-lg border border-border bg-secondary/40 px-3 py-1.5 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {providersList.map((p) => (
                <option key={p.key} value={p.key}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Mode tabs */}
        <div className="mb-6 grid grid-cols-4 gap-1 rounded-xl bg-secondary/50 p-1">
          {modeTabs.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
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
                  <span className="absolute h-full w-full animate-ping rounded-full bg-rose-500/20" />
                  <button
                    onClick={stopAudioRecording}
                    className="relative z-10 flex h-16 w-16 items-center justify-center rounded-full bg-rose-600 text-white transition-transform hover:scale-105 active:scale-95"
                  >
                    <Square className="h-6 w-6 fill-current" />
                  </button>
                </div>
                <div>
                  <p className="text-sm font-medium text-rose-400/90">Recording</p>
                  <p className="mt-1 text-2xl font-semibold tabular-nums">{formatTime(audioDuration)}</p>
                </div>
              </div>
            )}

            {audioUrl && !isRecordingAudio && (
              <div className="flex w-full max-w-md flex-col items-center gap-3">
                <div className="flex w-full items-center gap-3 rounded-xl border border-border bg-secondary/30 p-3">
                  <Mic className="h-5 w-5 shrink-0 text-accent-foreground" />
                  <audio src={audioUrl} controls className="h-8 w-full" />
                  <button
                    onClick={() => {
                      setAudioUrl(null);
                      setAudioBlob(null);
                    }}
                    className="text-muted transition-colors hover:text-foreground"
                    aria-label="Discard recording"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <p className="flex items-center gap-1.5 text-xs text-emerald-400/90">
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
                  <p className="flex items-center gap-1.5 text-xs text-emerald-400/90">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Captured {formatTime(videoDuration)}
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
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
              placeholder="A thought, a turning point, or a question for later you..."
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
              <p className="mt-3 flex items-center gap-1.5 text-xs text-emerald-400/90">
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
              className="w-full rounded-lg border border-border bg-secondary/30 px-3 py-2 text-xs text-foreground placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
        )}

        {error && (
          <div className="mt-4 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="mt-6 flex items-center justify-between gap-3 border-t border-border/60 pt-5">
          <span className="hidden items-center gap-1.5 text-xs text-muted sm:flex">
            <Sparkles className="h-3.5 w-3.5 text-accent-foreground" /> Grounded in your memory and timeline
          </span>

          <Button
            onClick={handleSubmit}
            disabled={isProcessing}
            className="gap-2 bg-primary px-5 text-primary-foreground"
          >
            {isProcessing ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Processing...
              </>
            ) : (
              <>
                <Send className="h-3.5 w-3.5" /> Remember this
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}