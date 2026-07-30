
import { Button } from "./ui/button";

const WhyMattersSection = () => {
  const points = [
    {
      number: "1",
      title: "Real Data, Not Guesswork",
      description: "This is the first publicly shared dataset of its kind in the PM industry—based on 89 verified, closed transactions, not hearsay or back-of-the-napkin estimates."
    },
    {
      number: "2",
      title: "Clear Valuation Benchmarks",
      description: "See what companies actually sold for—broken down by size, profit margin, buyer type, region, and more. If you're planning a sale, this helps you price realistically (and strategically)."
    },
    {
      number: "3",
      title: "Timing, Scale & Profit Insights You Can Use",
      description: "From the 350-door tipping point to profit-driven pricing and seasonal trends, this report reveals what really drives higher multiples—and how to leverage that insight whether you're buying or selling."
    }
  ];

  return (
    <div id="why-matters" className="bg-[#E4EEF4] py-16 px-4">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-[#1F2A36] mb-12 text-center">
          Why This Report Matters
        </h2>
        <div className="flex flex-col gap-8 mb-8">
          {points.map((point, index) => (
            <div key={index} className="p-8 bg-white shadow-lg transform hover:scale-[1.02] transition-transform rounded-lg">
              <div className="flex gap-6 items-start">
                <span className="text-4xl font-bold text-[#2D78A7] flex-shrink-0">
                  {point.number}
                </span>
                <div>
                  <h3 className="text-xl font-bold text-[#1F2A36] mb-3">
                    {point.title}
                  </h3>
                  <p className="text-[#1F2A36] text-lg">
                    {point.description}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
        {/* Button removed as per user request */}
      </div>
    </div>
  );
};

export default WhyMattersSection;
