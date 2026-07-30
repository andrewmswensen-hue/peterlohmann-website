
import { Card } from "@/components/ui/card";
import { CheckCircle } from "lucide-react";

const InsightsSection = () => {
  const insights = [
    "Revenue and profit multiple benchmarks across 89 transactions",
    "Key valuation trends by size, region, and buyer type",
    "Strategic insights for both buyers and sellers"
  ];

  return (
    <div id="insights" className="bg-white py-16 px-4">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-[#1F2A36] mb-8 text-center">
          What's Inside the Report
        </h2>
        <div className="grid md:grid-cols-3 gap-6">
          {insights.map((insight, index) => (
            <Card key={index} className="p-6 border-l-4 border-l-[#2D78A7] shadow-md">
              <div className="flex items-start gap-4">
                <CheckCircle className="text-[#56A68D] w-6 h-6 flex-shrink-0 mt-1" />
                <p className="text-lg text-[#1F2A36]">{insight}</p>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
};

export default InsightsSection;
