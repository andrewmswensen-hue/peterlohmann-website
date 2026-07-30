// Slim Peter Lohmann site strip so visitors on the M&A report can navigate back
// to any page of the main site. Non-sticky: it scrolls away and the report's own
// blue section-nav (CTABar) takes over — so there aren't two stacked sticky menus.
const links = [
  { href: "../index.html", label: "About" },
  { href: "../newsletter.html", label: "Newsletter" },
  { href: "../podcast.html", label: "Podcast" },
  { href: "../largest-pm-companies.html", label: "Largest PM Companies" },
  { href: "../blog.html", label: "Blog" },
  { href: "#", label: "M&A Report", active: true },
  { href: "../peterbot.html", label: "PeterBot" },
  { href: "../products.html", label: "Products" },
];

const SiteNav = () => (
  <div className="w-full bg-white border-b border-slate-200">
    <div className="max-w-6xl mx-auto px-4 py-2.5 flex items-center gap-5 overflow-x-auto whitespace-nowrap">
      <a href="../index.html" className="font-bold text-[17px] tracking-tight text-[#1F3A4D] shrink-0">
        Peter <span className="text-[#2C7CB0]">Lohmann</span>
      </a>
      <nav className="flex items-center gap-4 text-sm text-[#3d4d59] ml-1">
        {links.map((l) => (
          <a
            key={l.label}
            href={l.href}
            className={l.active ? "text-[#2C7CB0] font-semibold" : "hover:text-[#2C7CB0] transition-colors"}
          >
            {l.label}
          </a>
        ))}
      </nav>
    </div>
  </div>
);

export default SiteNav;
