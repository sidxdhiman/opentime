"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Mic,
  Video,
  FileText,
  Upload,
  Square,
  Play,
  Pause,
  Sparkles,
  Send,
  Cpu,
  CheckCircle2,
  AlertCircle,
  X,
  Volume2,
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
    { key: "chronos", name: "ChronOS Native Core Engine", model: "chronos-v1-core", badge: "Engine IP" },
    { key: "openai", name: "OpenAI GPT-4o", model: "gpt-4o", badge: "Cloud" },
    { key: "anthropic", name: "Claude 3.5 Sonnet", model: "claude-3-5-sonnet", badge: "Cloud" },
    { key: "gemini", name: "Google Gemini 1.5 Pro", model: "gemini-1.5-pro", badge: "Cloud" },
    { key: "ollama", name: "Ollama Local (Llama 3)", model: "llama3:latest", badge: "Privacy / Local" },
  ];

  // Cleanup on unmount
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

  // --- AUDIO RECORDING HANDLERS ---
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

  // --- VIDEO RECORDING HANDLERS ---
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

  // --- FILE UPLOAD HANDLER ---
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setUploadedFile(file);
    }
  };

  // --- SUBMIT TO CHRONOS ENGINE ---
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
          throw new Error("Please enter a text note or memory.");
        }
        formData.append("content", textContent);
        formData.append("input_type", "text");
      } else if (activeTab === "audio") {
        if (!audioBlob) {
          throw new Error("Please record a voice note first.");
        }
        formData.append("file", audioBlob, `voice_recording_${Date.now()}.webm`);
        formData.append("input_type", "audio");
        formData.append("content", textContent || "Voice recording memory log");
      } else if (activeTab === "video") {
        if (!videoBlob) {
          throw new Error("Please record a video note first.");
        }
        formData.append("file", videoBlob, `video_recording_${Date.now()}.webm`);
        formData.append("input_type", "video");
        formData.append("content", textContent || "Video recording memory log");
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

      // Reset state on success
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

  return (
    <Card className="border-border/80 bg-card/90 shadow-xl backdrop-blur">
      <CardContent className="p-6">
        {/* Engine Header & Model Swapper */}
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border/60 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-500 text-white shadow-lg shadow-violet-500/20">
              <Cpu className="h-5 w-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold tracking-tight text-foreground">ChronOS Engine</h3>
                <span className="rounded-full bg-violet-500/10 px-2.5 py-0.5 text-xs font-semibold text-violet-400 border border-violet-500/20">
                  Model-Agnostic Core
                </span>
              </div>
              <p className="text-xs text-muted">Input Processing Layer & Orchestrator</p>
            </div>
          </div>

          {/* Model Selector Dropdown */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted">LLM Provider:</span>
            <select
              value={selectedProvider}
              onChange={(e) => {
                const provKey = e.target.value;
                setSelectedProvider(provKey);
                const found = providersList.find((p) => p.key === provKey);
                if (found) setSelectedModel(found.model);
              }}
              className="rounded-lg border border-border bg-secondary px-3 py-1.5 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500"
            >
              {providersList.map((p) => (
                <option key={p.key} value={p.key}>
                  {p.name} [{p.badge}]
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Input Mode Selector Tabs */}
        <div className="mb-5 grid grid-cols-4 gap-2 rounded-xl bg-secondary/50 p-1.5">
          <button
            onClick={() => setActiveTab("audio")}
            className={`flex items-center justify-center gap-2 rounded-lg py-2 text-xs font-semibold transition-all ${
              activeTab === "audio"
                ? "bg-violet-600 text-white shadow-md shadow-violet-600/30"
                : "text-muted hover:text-foreground"
            }`}
          >
            <Mic className="h-4 w-4" />
            Record Voice
          </button>
          <button
            onClick={() => setActiveTab("video")}
            className={`flex items-center justify-center gap-2 rounded-lg py-2 text-xs font-semibold transition-all ${
              activeTab === "video"
                ? "bg-violet-600 text-white shadow-md shadow-violet-600/30"
                : "text-muted hover:text-foreground"
            }`}
          >
            <Video className="h-4 w-4" />
            Record Video
          </button>
          <button
            onClick={() => setActiveTab("text")}
            className={`flex items-center justify-center gap-2 rounded-lg py-2 text-xs font-semibold transition-all ${
              activeTab === "text"
                ? "bg-violet-600 text-white shadow-md shadow-violet-600/30"
                : "text-muted hover:text-foreground"
            }`}
          >
            <FileText className="h-4 w-4" />
            Text Memory
          </button>
          <button
            onClick={() => setActiveTab("upload")}
            className={`flex items-center justify-center gap-2 rounded-lg py-2 text-xs font-semibold transition-all ${
              activeTab === "upload"
                ? "bg-violet-600 text-white shadow-md shadow-violet-600/30"
                : "text-muted hover:text-foreground"
            }`}
          >
            <Upload className="h-4 w-4" />
            Upload File
          </button>
        </div>

        {/* TAB 1: RECORD VOICE */}
        {activeTab === "audio" && (
          <div className="flex flex-col items-center justify-center py-6 text-center">
            {!isRecordingAudio && !audioUrl && (
              <div className="flex flex-col items-center gap-3">
                <button
                  onClick={startAudioRecording}
                  className="group relative flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-tr from-rose-500 to-violet-600 text-white shadow-xl shadow-rose-500/25 transition-transform hover:scale-105 active:scale-95"
                >
                  <Mic className="h-8 w-8" />
                  <span className="absolute -bottom-7 text-xs font-medium text-muted">
                    Click to Record Voice
                  </span>
                </button>
              </div>
            )}

            {isRecordingAudio && (
              <div className="flex flex-col items-center gap-4">
                <div className="relative flex h-24 w-24 items-center justify-center">
                  <span className="absolute h-full w-full animate-ping rounded-full bg-rose-500/30" />
                  <button
                    onClick={stopAudioRecording}
                    className="relative z-10 flex h-16 w-16 items-center justify-center rounded-full bg-rose-600 text-white shadow-lg shadow-rose-600/40"
                  >
                    <Square className="h-6 w-6 fill-current" />
                  </button>
                </div>
                <div>
                  <p className="text-sm font-semibold text-rose-400">Recording Voice...</p>
                  <p className="text-xl font-bold tracking-tight text-foreground font-mono">
                    {formatTime(audioDuration)}
                  </p>
                </div>
              </div>
            )}

            {audioUrl && !isRecordingAudio && (
              <div className="w-full flex flex-col items-center gap-3">
                <div className="flex items-center gap-3 rounded-xl border border-border bg-secondary/80 p-3 w-full max-w-md">
                  <Volume2 className="h-5 w-5 text-violet-400 shrink-0" />
                  <audio src={audioUrl} controls className="w-full h-8" />
                  <button
                    onClick={() => {
                      setAudioUrl(null);
                      setAudioBlob(null);
                    }}
                    className="text-muted hover:text-foreground"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <span className="text-xs text-emerald-400 flex items-center gap-1 font-medium">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Voice recorded successfully ({formatTime(audioDuration)})
                </span>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: RECORD VIDEO */}
        {activeTab === "video" && (
          <div className="flex flex-col items-center justify-center py-4 text-center">
            {!isRecordingVideo && !videoUrl && (
              <div className="flex flex-col items-center gap-3">
                <button
                  onClick={startVideoRecording}
                  className="group relative flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-tr from-indigo-500 to-cyan-500 text-white shadow-xl shadow-indigo-500/25 transition-transform hover:scale-105 active:scale-95"
                >
                  <Video className="h-8 w-8" />
                  <span className="absolute -bottom-7 text-xs font-medium text-muted">
                    Click to Start Camera & Record
                  </span>
                </button>
              </div>
            )}

            {isRecordingVideo && (
              <div className="flex flex-col items-center gap-3 w-full max-w-md">
                <div className="relative overflow-hidden rounded-xl border border-indigo-500/40 bg-black aspect-video w-full">
                  <video ref={videoLiveRef} muted className="h-full w-full object-cover" />
                  <div className="absolute top-3 left-3 flex items-center gap-2 rounded-full bg-black/60 px-3 py-1 text-xs font-medium text-rose-400 backdrop-blur">
                    <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse" />
                    REC {formatTime(videoDuration)}
                  </div>
                </div>
                <Button variant="destructive" onClick={stopVideoRecording} className="gap-2">
                  <Square className="h-4 w-4 fill-current" /> Stop Video Recording
                </Button>
              </div>
            )}

            {videoUrl && !isRecordingVideo && (
              <div className="w-full flex flex-col items-center gap-3">
                <div className="relative overflow-hidden rounded-xl border border-border bg-black aspect-video w-full max-w-md">
                  <video src={videoUrl} controls className="h-full w-full object-cover" />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-emerald-400 flex items-center gap-1 font-medium">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Video note captured ({formatTime(videoDuration)})
                  </span>
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
              placeholder="Record a thought, belief shift, goal update, or question for ChronOS..."
              className="w-full h-28 rounded-xl border border-border bg-secondary/50 p-4 text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none"
            />
          </div>
        )}

        {/* TAB 4: FILE UPLOAD */}
        {activeTab === "upload" && (
          <div className="py-4 flex flex-col items-center justify-center border-2 border-dashed border-border/80 rounded-xl p-6 bg-secondary/20">
            <Upload className="h-8 w-8 text-muted mb-2" />
            <p className="text-sm font-medium text-foreground">Upload Voice, Video, or Document</p>
            <p className="text-xs text-muted mt-1">Supports MP3, WAV, MP4, WEBM, M4A, TXT</p>
            <input
              type="file"
              onChange={handleFileUpload}
              accept="audio/*,video/*,text/*"
              className="mt-4 text-xs text-muted file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-violet-600 file:text-white hover:file:bg-violet-700 cursor-pointer"
            />
            {uploadedFile && (
              <span className="mt-3 text-xs text-emerald-400 flex items-center gap-1 font-medium">
                <CheckCircle2 className="h-3.5 w-3.5" /> Selected: {uploadedFile.name} ({(uploadedFile.size / 1024).toFixed(1)} KB)
              </span>
            )}
          </div>
        )}

        {/* Additional Context Note for Voice/Video/Upload */}
        {activeTab !== "text" && (
          <div className="mt-4">
            <input
              type="text"
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              placeholder="Optional title or note for this media recording..."
              className="w-full rounded-lg border border-border bg-secondary/50 px-3 py-2 text-xs text-foreground placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-violet-500"
            />
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className="mt-4 flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Action Button */}
        <div className="mt-5 flex items-center justify-between border-t border-border/60 pt-4">
          <span className="text-xs text-muted flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-violet-400" /> Grounded in memory graph & timeline
          </span>

          <Button
            onClick={handleSubmit}
            disabled={isProcessing}
            className="bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-500 hover:to-indigo-500 shadow-md shadow-violet-600/30 gap-2 font-semibold text-xs px-5 py-2.5 h-auto rounded-xl"
          >
            {isProcessing ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Processing through ChronOS...
              </>
            ) : (
              <>
                <Send className="h-3.5 w-3.5" />
                Process with ChronOS
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
