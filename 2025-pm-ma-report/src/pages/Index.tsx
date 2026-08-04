
import SiteNav from "@/components/SiteNav";
import HeroSection from "@/components/HeroSection";
import InsightsSection from "@/components/InsightsSection";
import WhyMattersSection from "@/components/WhyMattersSection";
import AudienceSection from "@/components/AudienceSection";
import DifferentSection from "@/components/DifferentSection";
import AuthorSection from "@/components/AuthorSection";
import VideoSection from "@/components/VideoSection";
import CTABar from "@/components/CTABar";
import BackToSite from "@/components/BackToSite";
import Footer from "@/components/Footer";

const Index = () => {
  return (
    <div className="min-h-screen bg-white">
      <BackToSite />
      <SiteNav />
      <CTABar />
      <HeroSection />
      <WhyMattersSection />
      <DifferentSection />
      <VideoSection />
      <InsightsSection />
      <AudienceSection />
      <AuthorSection />
      <Footer />
    </div>
  );
};

export default Index;
