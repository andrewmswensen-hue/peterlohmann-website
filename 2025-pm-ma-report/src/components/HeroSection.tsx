
import { Button } from "@/components/ui/button";

const HeroSection = () => {
  const handlePurchase = () => {
    window.open("https://buy.stripe.com/00w9ASfwagYdalc5lD08g0g", "_blank", "noopener,noreferrer");
  };

  const scrollToDifferent = () => {
    const differentSection = document.getElementById('different');
    differentSection?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div id="hero" className="min-h-[80vh] flex items-center bg-gradient-to-b from-[#1F2A36] to-[#2D78A7] text-white px-4 py-16">
      <div className="max-w-7xl mx-auto grid md:grid-cols-2 gap-8 items-center">
        <div className="text-left">
          <h1 className="text-4xl md:text-6xl font-bold mb-6 leading-tight">
            What's A Property Management Company Actually Worth?
          </h1>
          <p className="text-xl md:text-2xl mb-8 text-[#E4EEF4]">
            Discover real-world data from 89 closed PM company transactions.
            The most detailed M&A (Mergers and Acquisitions) dataset ever shared for both buyers and sellers in the property management industry.
          </p>
          <div className="flex flex-col md:flex-row items-center md:items-start gap-4">
            <Button 
              onClick={handlePurchase}
              className="bg-[#56A68D] hover:bg-[#4a917a] text-white text-lg px-8 py-6 rounded-lg shadow-lg transition-all w-full md:w-auto"
            >
              Buy the Report
            </Button>
            <Button 
              onClick={scrollToDifferent}
              variant="outline"
              className="bg-transparent border-2 border-white hover:bg-white/10 text-white text-lg px-8 py-6 rounded-lg shadow-lg transition-all w-full md:w-auto"
            >
              More Info
            </Button>
          </div>
        </div>
        <div className="relative h-full min-h-[400px] rounded-lg overflow-hidden shadow-xl">
          <img
            src="lovable-uploads/b4ec2a35-4c6c-45af-ab5d-98503d95e5b5.png"
            alt="Property Management M&A Report"
            className="w-full h-full object-cover rounded-lg border border-[#f2f2f2]"
          />
        </div>
      </div>
    </div>
  );
};

export default HeroSection;
