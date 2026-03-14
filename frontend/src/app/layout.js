import "./globals.css";

export const metadata = {
  title: "Health Companion",
  description: "AI Health Companion Chatbot",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="flex justify-center items-center min-h-screen bg-gray-200">
        <div className="w-[393px] h-[852px] bg-cream relative overflow-hidden shadow-xl rounded-[40px] border-[8px] border-gray-800">
          {children}
        </div>
      </body>
    </html>
  );
}
