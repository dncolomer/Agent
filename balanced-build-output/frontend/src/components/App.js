import React from 'react';
import { BrowserRouter as Router, Route, Switch } from 'react-router-dom';
import HomePage from './HomePage';
import AboutPage from './AboutPage';
import ContactPage from './ContactPage';
import NotFoundPage from './NotFoundPage';

/**
 * Main App component that serves as the entry point for the front-end application.
 * It sets up routing for the application and ensures a clean and accessible user interface.
 */
function App() {
  return (
    <Router>
      <div className="app-container">
        <Switch>
          {/* Define routes for the application */}
          <Route exact path="/" component={HomePage} />
          <Route path="/about" component={AboutPage} />
          <Route path="/contact" component={ContactPage} />
          {/* Fallback route for 404 Not Found */}
          <Route component={NotFoundPage} />
        </Switch>
      </div>
    </Router>
  );
}

export default App;