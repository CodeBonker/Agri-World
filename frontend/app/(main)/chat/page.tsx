"use client";

import { useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { AnimatePresence, motion } from "framer-motion";
import { toast } from "sonner";
import { SendHorizonal, Trash2 } from "lucide-react";
import { PageShell } from "@/components/layout/page-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Markdown } from "@/components/ui/markdown";
import { useAutoScroll } from "@/hooks/use-auto-scroll";
import { clearChatSession, postChat } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string>("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSessionId(uuidv4());
  }, []);

  useAutoScroll(listRef, [messages]);

  const submitMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    const query = input.trim();
    if (!query || !sessionId || loading) return;

    const userMessage: ChatMessage = {
      id: uuidv4(),
      role: "user",
      content: query,
      timestamp: Date.now(),
    };

    const pendingAiId = uuidv4();
    const pendingMessage: ChatMessage = {
      id: pendingAiId,
      role: "ai",
      content: "Typing...",
      timestamp: Date.now(),
      pending: true,
    };

    setMessages((prev) => [...prev, userMessage, pendingMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await postChat({ query, session_id: sessionId });
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === pendingAiId
            ? {
                ...msg,
                pending: false,
                content: response.explanation,
              }
            : msg
        )
      );
    } catch (error: any) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === pendingAiId
            ? {
                ...msg,
                pending: false,
                error: true,
                content: error.message || "Chat request failed.",
              }
            : msg
        )
      );
      toast.error(error.message || "Unable to send message");
    } finally {
      setLoading(false);
    }
  };

  const resetSession = async () => {
    if (!sessionId) return;
    try {
      await clearChatSession(sessionId);
    } catch {
      // keep UI reset even if backend clear fails
    }
    setMessages([]);
    setSessionId(uuidv4());
    toast.success("New chat session started");
  };

  return (
    <PageShell>
      <div className="grid gap-4">
        <Card className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold">AI Chat Assistant</h2>
            <p className="mt-1 text-xs text-slate-500">
              Session: {sessionId || "Generating..."}
            </p>
          </div>
          <Button variant="ghost" onClick={resetSession} className="gap-2">
            <Trash2 className="h-4 w-4" />
            New Session
          </Button>
        </Card>

        <Card className="flex h-[65vh] flex-col p-0">
          <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.length === 0 && (
              <div className="flex h-full items-center justify-center text-sm text-slate-500 dark:text-slate-400">
                Ask anything about crops, fertilizers, weather, or diseases.
              </div>
            )}
            <AnimatePresence>
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-sm ${
                      message.role === "user"
                        ? "bg-brand-600 text-white"
                        : message.error
                        ? "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300"
                        : "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100"
                    }`}
                  >
                    {message.role === "ai" ? (
                      <Markdown content={message.content} />
                    ) : (
                      message.content
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>

          <form onSubmit={submitMessage} className="border-t border-slate-200 p-3 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message..."
                maxLength={2000}
              />
              <Button
                type="submit"
                disabled={loading || !sessionId || !input.trim()}
                className="h-11 w-11 p-0"
                aria-label="Send message"
              >
                <SendHorizonal className="h-4 w-4" />
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </PageShell>
  );
}
