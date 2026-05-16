// Inline lucide-style icons. Stroke 1.5, square caps for enterprise feel.
const I = ({ children, size = 16, className = "", strokeWidth = 1.6, ...rest }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size}
       viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round"
       className={className} {...rest}>
    {children}
  </svg>
);

const ArrowRight = (p) => <I {...p}><path d="M5 12h14"/><path d="M12 5l7 7-7 7"/></I>;
const ChevronRight = (p) => <I {...p}><path d="M9 6l6 6-6 6"/></I>;
const ChevronDown = (p) => <I {...p}><path d="M6 9l6 6 6-6"/></I>;
const Check = (p) => <I {...p}><path d="M20 6L9 17l-5-5"/></I>;
const X = (p) => <I {...p}><path d="M18 6L6 18M6 6l12 12"/></I>;
const Plus = (p) => <I {...p}><path d="M12 5v14M5 12h14"/></I>;
const Minus = (p) => <I {...p}><path d="M5 12h14"/></I>;
const Alert = (p) => <I {...p}><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></I>;
const FileText = (p) => <I {...p}><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></I>;
const Mic = (p) => <I {...p}><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></I>;
const Code = (p) => <I {...p}><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></I>;
const Image = (p) => <I {...p}><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></I>;
const Video = (p) => <I {...p}><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/></I>;
const Search = (p) => <I {...p}><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></I>;
const Shapes = (p) => <I {...p}><path d="M8.3 10a.7.7 0 01-.626-1.079L11.4 3a.7.7 0 011.198-.043L16.3 8.9a.7.7 0 01-.572 1.1z"/><rect x="3" y="14" width="7" height="7" rx="1"/><circle cx="17.5" cy="17.5" r="3.5"/></I>;
const Zap = (p) => <I {...p}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></I>;
const Server = (p) => <I {...p}><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></I>;
const Boxes = (p) => <I {...p}><path d="M2.97 12.92A2 2 0 002 14.63v3.24a2 2 0 00.97 1.71l3 1.8a2 2 0 002.06 0L12 19.06V14L7 11l-4.03 1.92z"/><path d="M7 16.5l-4.74-2.85"/><path d="M7 16.5l5-3"/><path d="M7 16.5v5.17"/><path d="M12 19.06L17.97 22.6a2 2 0 002.06 0l3-1.8a2 2 0 00.97-1.71v-3.24a2 2 0 00-.97-1.71L17 11l-5 3"/></I>;
const GitPullReq = (p) => <I {...p}><circle cx="6" cy="6" r="3"/><path d="M6 9v12"/><circle cx="18" cy="18" r="3"/><path d="M13 6h3a2 2 0 012 2v7"/></I>;
const Shield = (p) => <I {...p}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></I>;
const Rocket = (p) => <I {...p}><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 00-2.91-.09z"/><path d="M12 15l-3-3a22 22 0 012-3.95A12.88 12.88 0 0122 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 01-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/></I>;
const Lock = (p) => <I {...p}><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></I>;
const Eye = (p) => <I {...p}><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></I>;
const Building = (p) => <I {...p}><rect x="3" y="2" width="18" height="20" rx="1"/><path d="M9 22V12h6v10"/><line x1="7" y1="6" x2="7" y2="6.01"/><line x1="11" y1="6" x2="11" y2="6.01"/><line x1="15" y1="6" x2="15" y2="6.01"/><line x1="7" y1="10" x2="7" y2="10.01"/></I>;
const Users = (p) => <I {...p}><path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></I>;
const Layers = (p) => <I {...p}><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></I>;
const Activity = (p) => <I {...p}><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></I>;
const Globe = (p) => <I {...p}><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></I>;
const ArrowUpRight = (p) => <I {...p}><line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/></I>;
const Workflow = (p) => <I {...p}><rect x="3" y="3" width="6" height="6" rx="1"/><rect x="15" y="15" width="6" height="6" rx="1"/><path d="M9 6h6a3 3 0 013 3v6"/></I>;
const Gauge = (p) => <I {...p}><path d="M12 14l4-4"/><path d="M3.34 19a10 10 0 1117.32 0"/></I>;
const Terminal = (p) => <I {...p}><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></I>;
const Sliders = (p) => <I {...p}><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="2" y1="14" x2="6" y2="14"/><line x1="10" y1="8" x2="14" y2="8"/><line x1="18" y1="16" x2="22" y2="16"/></I>;

window.Icons = { ArrowRight, ChevronRight, ChevronDown, Check, X, Plus, Minus, Alert, FileText, Mic, Code, Image, Video, Search, Shapes, Zap, Server, Boxes, GitPullReq, Shield, Rocket, Lock, Eye, Building, Users, Layers, Activity, Globe, ArrowUpRight, Workflow, Gauge, Terminal, Sliders };
