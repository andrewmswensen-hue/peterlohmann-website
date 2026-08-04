import { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { cn } from "@/lib/utils";
import { Dot } from "lucide-react";

const CTABar = () => {
  const [showTopLink, setShowTopLink] = useState(false);
  
  useEffect(() => {
    const handleScroll = () => {
      const heroSection = document.getElementById('hero');
      if (heroSection) {
        const heroBottom = heroSection.offsetTop + heroSection.offsetHeight;
        setShowTopLink(window.scrollY > heroBottom);
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handlePurchase = () => {
    window.open("https://buy.stripe.com/00w9ASfwagYdalc5lD08g0g", "_blank");
  };

  const scrollToSection = (sectionId: string) => {
    const section = document.getElementById(sectionId);
    section?.scrollIntoView({ behavior: 'smooth' });
  };

  const navLinks = [
    ...(showTopLink ? [{ id: 'hero', label: 'Top' }] : []),
    { id: 'why-matters', label: 'Why This Matters' },
    { id: 'different', label: 'What Makes This Different' },
    { id: 'insights', label: 'Inside the Report' },
    { id: 'audience', label: 'Who This Is For' },
    { id: 'author', label: 'About the Author' },
  ];

  return (
    <div id="report-cta-bar" className="bg-[#2D78A7] py-8 px-4 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-4 overflow-x-auto whitespace-nowrap">
          {navLinks.map((link, index) => (
            <>
              <button
                key={link.id}
                onClick={() => scrollToSection(link.id)}
                className={cn(
                  "text-[#E4EEF4] hover:text-[#56A68D] hover:font-bold transition-all text-sm",
                  "focus:outline-none focus:underline"
                )}
              >
                {link.label}
              </button>
              {index < navLinks.length - 1 && (
                <Dot className="text-[#56A68D] w-4 h-4" />
              )}
            </>
          ))}
        </div>
        <Button
          onClick={handlePurchase}
          className="bg-[#56A68D] hover:bg-[#4a917a] text-white px-6 py-2 whitespace-nowrap"
        >
          Get Full Access
        </Button>
      </div>
    </div>
  );
};

export default CTABar;
