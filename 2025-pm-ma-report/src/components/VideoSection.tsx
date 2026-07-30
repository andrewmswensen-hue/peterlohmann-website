
const VideoSection = () => {
  return (
    <div className="bg-[#f5f7fa] py-16 px-4">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-[#1F2A36] mb-8 text-center">
          A Message From The Author, Peter Lohmann
        </h2>
        <div className="max-w-3xl mx-auto">
          <div style={{ position: "relative", paddingBottom: "56.25%", height: 0 }}>
            <iframe 
              src="https://www.loom.com/embed/091737f84528492cb534effc011e4fc2?sid=e20c6f16-ceae-44d0-bf45-112d918f8653" 
              frameBorder="0" 
              style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%" }}
              allowFullScreen
            ></iframe>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoSection;
