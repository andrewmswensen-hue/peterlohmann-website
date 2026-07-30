
import { Card } from "./ui/card";
import { Users } from "lucide-react";
import { Button } from "./ui/button";

const AudienceSection = () => {
  const handlePurchase = () => {
    window.open("https://buy.stripe.com/00w9ASfwagYdalc5lD08g0g", "_blank", "noopener,noreferrer");
  };

  const audiences = [
    {
      title: "PM Company Owners",
      description: "Planning for a sale or considering an acquisition"
    },
    {
      title: "Investors & Acquirers",
      description: "Evaluating or actively acquiring property management firms"
    },
    {
      title: "Industry Advisors",
      description: "Needing up-to-date market benchmarks"
    },
    {
      title: "Operators",
      description: "Curious how size, margins, or geography impact valuation"
    }
  ];

  return (
    <div id="audience" className="bg-white py-16 px-4">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-[#1F2A36] mb-8 text-center">
          Who This Is For
        </h2>
        <div className="grid md:grid-cols-2 gap-6">
          {audiences.map((audience, index) => (
            <Card key={index} className="p-6 border-l-4 border-l-[#56A68D] shadow-md">
              <div className="flex items-start gap-4">
                <Users className="text-[#2D78A7] w-6 h-6 flex-shrink-0 mt-1" />
                <div>
                  <h3 className="font-bold text-xl mb-2 text-[#1F2A36]">{audience.title}</h3>
                  <p className="text-[#1F2A36]">{audience.description}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
        <div className="mt-12 flex justify-center">
          <Button 
            onClick={handlePurchase}
            className="bg-[#56A68D] hover:bg-[#4a917a] text-white text-lg px-8 py-6 rounded-lg shadow-lg transition-all"
          >
            Get Your Copy Now
          </Button>
        </div>
      </div>
    </div>
  );
};

export default AudienceSection;
