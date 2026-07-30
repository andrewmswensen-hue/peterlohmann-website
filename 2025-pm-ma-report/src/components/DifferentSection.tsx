
import { AspectRatio } from "./ui/aspect-ratio";
import { Button } from "./ui/button";

const DifferentSection = () => {
  const checkPoints = [
    {
      emoji: "🏘️",
      text: "Based on 89 real, closed transactions (not inflated listings or unverifiable hearsay)"
    },
    {
      emoji: "🔍",
      text: "Personally reviewed by a fellow PM owner for accuracy, consistency, and realism"
    },
    {
      emoji: "📊",
      text: "Breaks down multiples by size, profit margin, buyer type, region, and more"
    },
    {
      emoji: "📆",
      text: "Tracks 5 years of deal data (2020–2025) to show how valuation trends are shifting"
    },
    {
      emoji: "💡",
      text: "Includes insights you won't find in any broker pitch or blog post"
    }
  ];

  const handlePurchase = () => {
    window.open("https://buy.stripe.com/00w9ASfwagYdalc5lD08g0g", "_blank", "noopener,noreferrer");
  };

  return (
    <div id="different" className="bg-[#1F2A36] py-16 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="grid md:grid-cols-2 gap-12">
          <div className="text-white space-y-8">
            <h2 className="text-3xl md:text-4xl font-bold mb-8">
              What Makes This Different
            </h2>
            
            <div className="space-y-2 text-xl opacity-90 mb-8 font-semibold">
              <p>You've probably heard stories…</p>
              <p className="italic ml-4 text-[#56A68D]">"You're worth 2× revenue."</p>
              <p className="italic ml-4 text-[#56A68D]">"Rollups will pay anything."</p>
              <p className="italic ml-4 text-[#56A68D]">"Size is all that matters."</p>
            </div>

            <p className="text-lg mb-8">
              This report moves past the anecdotes and rumors. It's the first independent look at what property management companies actually sell for—and why.
            </p>

            <ul className="space-y-4">
              {checkPoints.map((point, index) => (
                <li key={index} className="flex gap-3 items-start">
                  <span className="text-2xl">{point.emoji}</span>
                  <span>{point.text}</span>
                </li>
              ))}
            </ul>
            
            <p className="text-lg mt-4">
              Whether you're a PM company owner, buyer, or advisor, this is the most concrete dataset available to guide valuation decisions on both sides of the table.
            </p>

            <div className="mt-12 pt-6 border-t border-white/10">
              <blockquote className="text-lg italic">
                "Property managers have been operating in the dark. This report gives us a baseline for real acquisition data."
              </blockquote>
              <p className="mt-2 text-[#56A68D]">— Peter Lohmann, Author</p>
            </div>
          </div>

          <div className="space-y-6">
            <p className="text-center text-gray-400 text-sm mb-2">A peek inside the report...</p>
            <div className="bg-white rounded-lg p-6">
              <AspectRatio ratio={16/9}>
                <img 
                  src="lovable-uploads/88768150-117c-4d05-ab31-0bdc42cf0107.png"
                  alt="Methodology and Data Overview"
                  className="w-full h-full object-contain rounded-lg"
                />
              </AspectRatio>
            </div>
            
            <div className="bg-white rounded-lg p-6">
              <AspectRatio ratio={16/9}>
                <img 
                  src="lovable-uploads/9173743d-5220-4b87-afe9-0d067d0e3b5d.png"
                  alt="Profit Multiple Patterns"
                  className="w-full h-full object-contain rounded-lg"
                />
              </AspectRatio>
            </div>
            
            <div className="mt-6">
              <div className="bg-white rounded-lg p-4 flex items-center">
                <div className="w-1/2 pr-3">
                  <p className="text-black text-lg font-medium mb-2">Sponsored by</p>
                  <img 
                    src="lovable-uploads/b460f6ec-f5ef-4e93-a15c-3e21131b51b0.png"
                    alt="Enterprise Bank & Trust Logo"
                    className="max-h-24 object-contain"
                  />
                </div>
                <div className="w-1/2 pl-3 border-l border-gray-200">
                  <p className="text-black text-sm italic">
                    "Whether you're a buyer or seller, this report shines light on the fact that the PM industry is an incredible place to be in 2025!"
                  </p>
                  <p className="text-sm font-medium text-[#56A68D] mt-1">
                    - Allison DiSarro<br />Senior VP - PM Banking Division
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-12 flex justify-center">
          <Button 
            onClick={handlePurchase}
            className="bg-[#56A68D] hover:bg-[#4a917a] text-white px-8 py-3 text-lg"
          >
            Buy the Report
          </Button>
        </div>
      </div>
    </div>
  );
};

export default DifferentSection;
