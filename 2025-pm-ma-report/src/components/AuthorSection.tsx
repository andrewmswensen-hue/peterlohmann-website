
import { Button } from "@/components/ui/button";
import { ExternalLink } from "lucide-react";

const AuthorSection = () => {
  return (
    <div id="author" className="bg-[#BFD6E4] py-16 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white p-8 rounded-lg shadow-lg">
          <h2 className="text-3xl font-bold text-[#1F2A36] mb-6">About the Author, Peter Lohmann</h2>
          <div className="md:flex gap-8 items-start">
            <div className="flex flex-col items-center">
              <img 
                src="lovable-uploads/db211062-db43-474d-950d-e7e992b53129.png"
                alt="Peter Lohmann"
                className="w-48 h-48 object-cover rounded-lg mb-4"
              />
              <Button 
                variant="outline" 
                className="flex items-center gap-2 w-full" 
                onClick={() => window.open("../index.html", "_blank", "noopener noreferrer")}
              >
                Peter's Website
                <ExternalLink className="h-4 w-4" />
              </Button>
            </div>
            <div className="text-[#1F2A36] space-y-4 mt-6 md:mt-0">
              <p>
                Peter Lohmann is the co-founder of RL Property Management, a Columbus, Ohio-based company that manages nearly 700 residential rentals. He holds a degree in electrical engineering from Geneva College and brings that same precision to the way he approaches business, data, systems, and valuation.
              </p>
              <p>
                Peter writes a <a href="https://peter.beehiiv.com/subscribe" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">weekly newsletter</a> read by over 15,000 property management professionals, speaks at national industry events, and is the co-founder of CRANE, a private community for PM company owners. Peter has been on both sides of the table—as a buyer, seller, and advisor in multiple PM transactions. He created this report to bring clarity and credibility to an M&A space that's long relied on hearsay instead of hard numbers (he also just really likes spreadsheets).
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthorSection;
