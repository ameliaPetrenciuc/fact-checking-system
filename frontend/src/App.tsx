import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { FactCheckPage } from "./pages/FactCheckPage";
import { DashboardPage } from "./pages/DashboardPage";
import { Navbar } from "./components/Navbar";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-background">
        <Navbar />
        <Routes>
          <Route path="/fact-check" element={<FactCheckPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="*" element={<Navigate to="/fact-check" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
