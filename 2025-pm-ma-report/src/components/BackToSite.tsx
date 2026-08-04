import { useState, useEffect } from "react";

// Floating "Back to PeterLohmann.com" pill. Appears in the top-right once the
// site strip (the full Peter Lohmann nav) has scrolled out of view, so visitors
// always have a one-click way back to the main site.
const BackToSite = () => {
  const [show, setShow] = useState(false);
  const [top, setTop] = useState(14); // sits just below the sticky CTA bar so it never covers "Get Full Access"

  useEffect(() => {
    const onScroll = () => {
      const strip = document.getElementById("site-strip");
      const bar = document.getElementById("report-cta-bar");
      const stripH = strip ? strip.offsetHeight : 60;
      setShow(window.scrollY > stripH); // show once the site strip has scrolled away
      if (bar) setTop(bar.offsetHeight + 12); // sit just below the sticky CTA bar
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, []);

  return (
    <a
      href="../index.html"
      aria-label="Back to PeterLohmann.com"
      style={{
        position: "fixed",
        top: `${top}px`,
        right: "16px",
        zIndex: 60,
        display: "inline-flex",
        alignItems: "center",
        gap: "7px",
        padding: "9px 16px",
        borderRadius: "999px",
        background: "#ffffff",
        border: "1px solid #dce4ec",
        color: "#1F3A4D",
        fontWeight: 600,
        fontSize: "13.5px",
        lineHeight: 1,
        textDecoration: "none",
        boxShadow: "0 8px 24px rgba(31,58,77,.20)",
        opacity: show ? 1 : 0,
        transform: show ? "translateY(0)" : "translateY(-10px)",
        pointerEvents: show ? "auto" : "none",
        transition: "opacity .3s ease, transform .3s ease",
      }}
    >
      <span aria-hidden="true" style={{ fontSize: "15px" }}>&larr;</span>
      Back to PeterLohmann.com
    </a>
  );
};

export default BackToSite;
