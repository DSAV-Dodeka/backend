import Auth from "./Auth";
import {Route, BrowserRouter as Router, Routes} from "react-router-dom";
import Register from "./Register";

function App() {
  return (
    <div className="page">
      <Router>
          <Routes>
              <Route path="/credentials" element={
                  <Auth />
              }/>
              <Route path="/credentials/register" element={
                  <Register />
              }/>
          </Routes>
      </Router>
    </div>
  )
}

export default App
