"use client";

import { useState, useEffect, FormEvent } from "react";
import Link from "next/link";

/* ───────────────────────────────────────────────
   Google Forms Configuration

   HOW TO SET UP:
   1. Go to https://docs.google.com/forms
   2. Create a form with these fields (in order):
      - Name (Short answer)
      - Company (Short answer)
      - Email (Short answer)
      - Phone (Short answer)
      - Message (Paragraph)
      - Page URL (Short answer)       ← hidden, auto-filled
      - Referrer (Short answer)        ← hidden, auto-filled
      - UTM Source (Short answer)      ← hidden, auto-filled
   3. Click "Send" → copy the form link
   4. Open the link, view page source, find:
      - Form action URL: look for <form action="https://docs.google.com/forms/u/0/d/e/XXXX/formResponse"
      - Entry IDs: look for entry.XXXXXXXXX for each field
   5. Replace the values below
   6. In Google Forms settings: enable email notifications
      (Responses tab → ⋮ menu → Get email notifications for new responses)
   7. Make sure the form response spreadsheet is linked to dheeraj.karnati07@gmail.com
   ─────────────────────────────────────────────── */

const GOOGLE_FORM_ACTION =
  "https://docs.google.com/forms/u/0/d/e/1FAIpQLSccLSKg2iGLsE5LzFcpLoiBHNYr5JNlJZREBd8z6CmSwjAApw/formResponse";

// Entry IDs extracted from Google Form HTML source data-params attributes
const FIELD_IDS = {
  name: "entry.2005620554",       // Name (sub-entry of question 1633920210)
  company: "entry.630605057",     // Company (sub-entry of question 840713990)
  email: "emailAddress",          // Email — Google's built-in email collection, not a regular entry
  phone: "entry.1166974658",      // Phone number (sub-entry of question 1770822543)
  message: "entry.839337160",     // Comments (sub-entry of question 1846923513)
  address: "entry.1065046570",    // Address (sub-entry of question 790080973) — used for page metadata
};

/* ───────────────────────────────────────────────
   Form Component
   ─────────────────────────────────────────────── */

interface FormData {
  name: string;
  company: string;
  email: string;
  phone: string;
  message: string;
}

export default function BookDemoPage() {
  const [form, setForm] = useState<FormData>({
    name: "",
    company: "",
    email: "",
    phone: "",
    message: "",
  });
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Capture page context (visible, non-invasive metadata)
  const [pageContext, setPageContext] = useState({ pageUrl: "", referrer: "", utmSource: "" });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setPageContext({
      pageUrl: window.location.href,
      referrer: document.referrer || "direct",
      utmSource: params.get("utm_source") || params.get("ref") || "organic",
    });
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setError("");
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    // Client-side validation
    if (!form.name.trim()) { setError("Please enter your name."); return; }
    if (!form.email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      setError("Please enter a valid email address.");
      return;
    }

    setSubmitting(true);

    try {
      // Build form data for Google Forms submission
      const formBody = new URLSearchParams();
      formBody.append(FIELD_IDS.name, form.name);
      formBody.append(FIELD_IDS.email, form.email);
      formBody.append(FIELD_IDS.company, form.company);
      formBody.append(FIELD_IDS.phone, form.phone);
      formBody.append(FIELD_IDS.message, form.message);
      // Pack page context into the Address field for tracking
      formBody.append(FIELD_IDS.address, [
        `URL: ${pageContext.pageUrl}`,
        `Referrer: ${pageContext.referrer}`,
        `UTM: ${pageContext.utmSource}`,
      ].join(" | "));

      // Submit to Google Forms (no-cors because Google doesn't return CORS headers)
      await fetch(GOOGLE_FORM_ACTION, {
        method: "POST",
        mode: "no-cors",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formBody.toString(),
      });

      // Google Forms always succeeds with no-cors (we can't read the response)
      setSubmitted(true);
    } catch {
      // Even network errors are swallowed by no-cors, but just in case
      setSubmitted(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-ink-900">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 bg-ink-900/95 backdrop-blur-md border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl font-black tracking-tighter">
              D8<span className="text-flame">X</span>
            </span>
          </Link>
          <div className="hidden md:flex items-center gap-8 text-sm text-gray-400">
            <Link href="/" className="hover:text-white transition-colors">Home</Link>
            <Link href="/demo" className="hover:text-white transition-colors">Live Demo</Link>
          </div>
        </div>
      </nav>

      <div className="pt-24 pb-16 max-w-6xl mx-auto px-6">
        <div className="grid lg:grid-cols-2 gap-16 items-start">

          {/* Left: Value prop */}
          <div className="lg:pt-8">
            <h1 className="text-4xl md:text-5xl font-black tracking-tight leading-tight">
              See D8X in action<br />
              <span className="text-flame">with your own project.</span>
            </h1>
            <p className="mt-6 text-lg text-gray-400 leading-relaxed">
              Book a 30-minute live demo where we run D8X on a sample from your
              codebase or requirements. No slides — just real agents producing real output.
            </p>

            <div className="mt-10 space-y-6">
              {[
                { icon: "🔍", title: "We analyze your inputs live", desc: "Upload a BRD, code files, or meeting notes — watch 8 agents process them in real time." },
                { icon: "📐", title: "You see the full output", desc: "Architecture decisions, database schema, API contracts, a live prototype URL — all generated from your data." },
                { icon: "🤝", title: "No commitment", desc: "It's a demo, not a sales pitch. If D8X isn't right for you, we'll tell you." },
              ].map((item) => (
                <div key={item.title} className="flex gap-4">
                  <span className="text-2xl mt-0.5">{item.icon}</span>
                  <div>
                    <h3 className="font-semibold text-white">{item.title}</h3>
                    <p className="text-sm text-gray-400 mt-1">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Trust signals */}
            <div className="mt-10 pt-8 border-t border-white/10">
              <div className="flex items-center gap-6 text-sm text-gray-500">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-flame" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Patent Pending
                </div>
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-flame" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  SOC2 Ready
                </div>
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-flame" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  On-Prem Available
                </div>
              </div>
            </div>
          </div>

          {/* Right: Cal.com scheduling + contact form */}
          <div className="space-y-6">
            {/* Cal.com instant scheduling — primary CTA */}
            <div className="rounded-2xl border border-flame/30 bg-gradient-to-b from-flame/5 to-transparent p-8 text-center">
              <div className="flex items-center justify-center gap-2 mb-3">
                <svg className="w-6 h-6 text-flame" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <h2 className="text-xl font-bold text-white">Schedule Instantly</h2>
              </div>
              <p className="text-sm text-gray-400 mb-5">Pick a time that works — calendar syncs automatically.</p>
              <a
                href="https://cal.com/d8x-demo"
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary justify-center w-full text-base"
              >
                Open Calendar
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>

            {/* Divider */}
            <div className="flex items-center gap-4">
              <div className="flex-1 h-px bg-white/10" />
              <span className="text-xs text-gray-500 uppercase tracking-wider">or leave a message</span>
              <div className="flex-1 h-px bg-white/10" />
            </div>

            {submitted ? (
              /* ─── Success State ─── */
              <div className="rounded-2xl border border-green-500/30 bg-gradient-to-b from-green-500/5 to-transparent p-10 text-center animate-fade-in">
                <div className="w-16 h-16 rounded-full bg-green-500/10 border-2 border-green-500/30 flex items-center justify-center mx-auto mb-6">
                  <svg className="w-8 h-8 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h2 className="text-2xl font-bold text-white mb-3">You're all set!</h2>
                <p className="text-gray-400 leading-relaxed mb-6">
                  Thanks, <span className="text-white font-medium">{form.name.split(" ")[0]}</span>!
                  We'll reach out to <span className="text-sky-400 font-medium">{form.email}</span> within
                  24 hours to schedule your live demo.
                </p>
                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                  <Link href="/demo" className="btn-secondary !py-3 !px-6 text-sm">
                    Watch the Walkthrough
                  </Link>
                  <Link href="/" className="px-6 py-3 text-sm text-gray-400 hover:text-white transition-colors">
                    Back to Home
                  </Link>
                </div>
              </div>
            ) : (
              /* ─── Form ─── */
              <form
                onSubmit={handleSubmit}
                className="rounded-2xl border border-white/10 bg-ink-800 p-8 space-y-5"
              >
                <div>
                  <h2 className="text-xl font-bold text-white">Book a Demo</h2>
                  <p className="text-sm text-gray-400 mt-1">Fill in the form and we'll schedule a live walkthrough.</p>
                </div>

                {/* Name */}
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-gray-300 mb-1.5">
                    Full Name <span className="text-flame">*</span>
                  </label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    value={form.name}
                    onChange={handleChange}
                    required
                    placeholder="Jane Smith"
                    className="w-full px-4 py-3 bg-ink-900 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-sky-500/50 focus:ring-1 focus:ring-sky-500/30 transition-colors"
                  />
                </div>

                {/* Company */}
                <div>
                  <label htmlFor="company" className="block text-sm font-medium text-gray-300 mb-1.5">
                    Company
                  </label>
                  <input
                    type="text"
                    id="company"
                    name="company"
                    value={form.company}
                    onChange={handleChange}
                    placeholder="Acme Corp"
                    className="w-full px-4 py-3 bg-ink-900 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-sky-500/50 focus:ring-1 focus:ring-sky-500/30 transition-colors"
                  />
                </div>

                {/* Email */}
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-1.5">
                    Work Email <span className="text-flame">*</span>
                  </label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={form.email}
                    onChange={handleChange}
                    required
                    placeholder="jane@acme.com"
                    className="w-full px-4 py-3 bg-ink-900 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-sky-500/50 focus:ring-1 focus:ring-sky-500/30 transition-colors"
                  />
                </div>

                {/* Phone */}
                <div>
                  <label htmlFor="phone" className="block text-sm font-medium text-gray-300 mb-1.5">
                    Phone Number
                  </label>
                  <input
                    type="tel"
                    id="phone"
                    name="phone"
                    value={form.phone}
                    onChange={handleChange}
                    placeholder="+1 (555) 123-4567"
                    className="w-full px-4 py-3 bg-ink-900 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-sky-500/50 focus:ring-1 focus:ring-sky-500/30 transition-colors"
                  />
                </div>

                {/* Message */}
                <div>
                  <label htmlFor="message" className="block text-sm font-medium text-gray-300 mb-1.5">
                    Tell us about your project
                  </label>
                  <textarea
                    id="message"
                    name="message"
                    value={form.message}
                    onChange={handleChange}
                    rows={4}
                    placeholder="We have a legacy VB6 application with 500K lines of code that needs modernization..."
                    className="w-full px-4 py-3 bg-ink-900 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-sky-500/50 focus:ring-1 focus:ring-sky-500/30 transition-colors resize-none"
                  />
                </div>

                {/* Error */}
                {error && (
                  <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2.5">
                    <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {error}
                  </div>
                )}

                {/* Submit */}
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full btn-primary justify-center text-base disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
                >
                  {submitting ? (
                    <>
                      <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Submitting...
                    </>
                  ) : (
                    <>
                      Book My Demo
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                      </svg>
                    </>
                  )}
                </button>

                <p className="text-xs text-gray-500 text-center">
                  We'll respond within 24 hours. No spam, no sales bots.
                </p>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
