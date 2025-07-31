import React, { useState, useEffect } from 'react';
import logo from './assets/hoopprophet-logo.svg';
import { motion } from 'framer-motion';

import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Container,
  Box,
  CssBaseline,
  ThemeProvider,
  createTheme,
  Autocomplete,
  TextField,
} from '@mui/material';

const theme = createTheme({
  palette: {
    primary: {
      main: '#7D8CC4',
    },
    secondary: {
      main: '#7067CF',
    },
    background: {
      default: '#e8f0ecff',
      paper: '#e8f0ecff',
    },
  },
  typography: {
    fontFamily: '"Lato", sans-serif', // Default for body
    h1: { fontFamily: '"Special Gothic Expanded One", "Lato", sans-serif' },
    h2: { fontFamily: '"Special Gothic Expanded One", "Lato", sans-serif' },
    h3: { fontFamily: '"Special Gothic Expanded One", "Lato", sans-serif' },
    h4: { fontFamily: '"Special Gothic Expanded One", "Lato", sans-serif' },
    h5: { fontFamily: '"Special Gothic Expanded One", "Lato", sans-serif' },
    h6: { fontFamily: '"Special Gothic Expanded One", "Lato", sans-serif' },
    subtitle1: { fontFamily: '"Lato", sans-serif' },
    subtitle2: { fontFamily: '"Lato", sans-serif' },
    body1: { fontFamily: '"Lato", sans-serif' },
    body2: { fontFamily: '"Lato", sans-serif' },
  },
});

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

function App() {
  const [players, setPlayers] = useState([]);
  const [teams, setTeams] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [loading, setLoading] = useState(true);
  const [predicting, setPredicting] = useState(false);
  const [predictions, setPredictions] = useState(null);
  const [predictionStatus, setPredictionStatus] = useState('');

  // Fetch NBA players and teams when component mounts
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch players and teams in parallel
        const [playersResponse, teamsResponse] = await Promise.all([
          fetch(`${API_BASE}/players`),
          fetch(`${API_BASE}/teams`)
        ]);
        
        const playersData = await playersResponse.json();
        const teamsData = await teamsResponse.json();
        
        setPlayers(playersData || []);
        setTeams(teamsData || []);
        console.log('Players data:', playersData?.slice(0, 5)); // Debug: show first 5 players
        console.log('Teams data:', teamsData?.slice(0, 5)); // Debug: show first 5 teams
        setLoading(false);
      } catch (error) {
        console.error('Error fetching data:', error);
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  function prettifyStatName(stat) {
  return stat
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

  const handlePredict = async () => {
      if (!selectedPlayer || !selectedTeam) return;
      
      setPredicting(true);
      setPredictionStatus('Starting prediction...');
      try {
        setPredictionStatus('Connecting to API...');
        const response = await fetch(`${API_BASE}/predict`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            player_name: selectedPlayer.full_name,
            opponent_team_abv: selectedTeam.abbreviation,
          }),
        });
        
        if (!response.ok) {
          throw new Error('Prediction failed');
        }
        
        setPredictionStatus('Processing results...');
        const data = await response.json();
        setPredictions(data);
        setPredictionStatus('Prediction complete!');
        setTimeout(() => setPredictionStatus(''), 2000); // Clear status after 2 seconds
      } catch (error) {
        console.error('Error making prediction:', error);
        setPredictionStatus('Prediction failed. Please try again.');
        setTimeout(() => setPredictionStatus(''), 3000);
      } finally {
        setPredicting(false);
      }
    };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      
      {/* Navigation */}
      <AppBar position="static">
        <Toolbar>
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            whileHover={{ scale: 1.15 }}
            style={{ display: "inline-block", marginRight: 8 }}
          >
            <Button color="inherit"><img src={logo} alt="HoopProphet Logo" height={36} /></Button>
          </motion.div>
        </Toolbar>
      </AppBar>

        <Box
          sx={{
            bgcolor: 'background.paper',
            pt: 8,
            pb: 6,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <Container maxWidth="lg" sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          style={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}
            >
          <Typography
            component="h1"
            variant="h2"
            align="center"
            color="text.primary"
            gutterBottom
          >
            HoopProphet
          </Typography>
          <Typography variant="h5" align="center" color="text.secondary" paragraph>
            Advanced Basketball Analytics & Predictions
          </Typography>
          <Typography
            variant="body1"
            align="center"
            sx={{ width: { xs: '100%', sm: '70%', md: '50%' }, mx: 'auto' }}
            color="text.secondary"
            paragraph
          >
            Leverage machine learning to predict game outcomes, analyze player performance, 
            and gain insights into basketball statistics like never before.
          </Typography>
            </motion.div>
          </Container>
        </Box>
        <Box
          sx={{
            bgcolor: 'background.paper',
            pt: 2,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <Container maxWidth="lg" sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          style={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}
            >
            <Typography
              component="h2"
              variant="h5"
              align="center"
              color="text.primary"
              gutterBottom
              sx={{ mb: 3 }}
            >
              Make Your Selections
            </Typography>
            
            <Box 
              sx={{ 
                display: 'flex', 
                gap: 3, 
                flexDirection: { xs: 'column', md: 'row' },
                alignItems: 'center',
                justifyContent: 'center',
                width: '100%'
              }}
            >
              {/* Player Selection */}
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  Select Player
                </Typography>
                <Autocomplete
                  disablePortal
                  options={players}
                  getOptionLabel={(option) => option.full_name || ""}
                  filterOptions={(options, { inputValue }) => {
                    if (!inputValue) return options;
                    const searchTerm = inputValue.toLowerCase().trim();
                    return options.filter(option => {
                      const fullName = (option.full_name || "").toLowerCase();
                      // Check if search term matches the beginning of first name, last name, or full name
                      const names = fullName.split(' ');
                      return fullName.includes(searchTerm) || 
                             names.some(name => name.startsWith(searchTerm));
                    });
                  }}
                  loading={loading}
                  value={selectedPlayer}
                  onChange={(event, newValue) => {
                    setSelectedPlayer(newValue);
                    console.log('Selected player:', newValue);
                  }}
                  sx={{ width: 350 }}
                  renderInput={(params) => (
                    <TextField 
                      {...params} 
                      label="Search NBA Players"
                      variant="outlined"
                      placeholder="Type player name..."
                    />
                  )}
                />
                <Box
                  sx={{
                    mt: 2,
                    width: 320,
                    height: 320,
                    borderRadius: 3,
                    bgcolor: '#f5f5f5',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: 1,
                    border: '2px solid #e0e0e0',
                    position: 'relative',
                    overflow: 'hidden',
                  }}
                >
                  {selectedPlayer ? (
                    <motion.img
                      key={selectedPlayer.id}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ duration: 0.5, ease: "easeOut" }}
                      src={`https://cdn.nba.com/headshots/nba/latest/1040x760/${selectedPlayer.id}.png`}
                      alt={`${selectedPlayer.full_name} headshot`}
                      style={{ 
                        position: 'relative',
                        bottom: 0,
                        maxWidth: '140%', 
                        maxHeight: '100%', 
                        width: 'auto'
                      }}
                      onError={e => (e.target.style.display = 'none')}
                    />
                  ) : (
                    <Typography variant="h5" color="text.secondary" justifyContent="center">
                      Player Headshot
                    </Typography>
                  )}
                </Box>
              </Box>

              {/* Team Selection */}
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  Opponent Team
                </Typography>
                <Autocomplete
                  disablePortal
                  options={teams}
                  getOptionLabel={(option) => option.full_name || ""}
                  filterOptions={(options, { inputValue }) => {
                    if (!inputValue) return options;
                    return options.filter(option =>
                      option.full_name.toLowerCase().includes(inputValue.toLowerCase())
                    );
                  }}
                  loading={loading}
                  value={selectedTeam}
                  onChange={(event, newValue) => {
                    setSelectedTeam(newValue);
                    console.log('Selected team:', newValue);
                  }}
                  sx={{ width: 350 }}
                  renderInput={(params) => (
                    <TextField 
                      {...params} 
                      label="Search NBA Teams"
                      variant="outlined"
                      placeholder="Type team name..."
                    />
                  )}
                />

              {/* Show logo if a team is selected */}
              <Box
            sx={{
              mt: 2,
              width: 320,
              height: 320,
              borderRadius: 3,
              bgcolor: '#f5f5f5',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: 1,
              border: '2px solid #e0e0e0',
            }}
          >
            {selectedTeam ? (
              <motion.img
                key={selectedTeam.id}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                src={`https://cdn.nba.com/logos/nba/${selectedTeam.id}/primary/L/logo.svg`}
                alt={`${selectedTeam.full_name} logo`}
                style={{ maxWidth: '90%', maxHeight: '90%' }}
                onError={e => (e.target.style.display = 'none')}
              />
            ) : (
              <Typography variant="h5" color="text.secondary" justifyContent="center">
                Team Logo
              </Typography>
            )}
          </Box>
              </Box>
            </Box>
            </motion.div>
          </Container>
        </Box>
  
<Box
  sx={{
    bgcolor: 'background.paper',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    }}>
        {selectedPlayer && selectedTeam && (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.5 }}
  >
    
    <Button
      variant="contained"
      size="large"
      onClick={handlePredict}
      disabled={predicting}
      sx={{
        mt: 4,
        px: 4,
        py: 2,
        fontFamily: "Special Gothic Expanded One, Lato, sans-serif",
        fontSize: '1.4rem',
      }}
    >
      {predicting ? 'Predicting...' : 'Predict Stats'}
    </Button>
    
    {/* Status display */}
    {predicting && predictionStatus && (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Typography
          variant="body1"
          align="center"
          sx={{
            mt: 2,
            color: 'primary.main',
            fontStyle: 'italic'
          }}
        >
          {predictionStatus}
        </Typography>
      </motion.div>
    )}
    
    {/* Error/Success status */}
    {!predicting && predictionStatus && (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Typography
          variant="body1"
          align="center"
          sx={{
            mt: 2,
            color: predictionStatus.includes('failed') ? 'error.main' : 'success.main',
            fontWeight: 'bold'
          }}
        >
          {predictionStatus}
        </Typography>
      </motion.div>
    )}
  </motion.div>
)}
</Box>

{/* Predictions Results */}
{predictions && (
  <Box
    sx={{
      bgcolor: 'background.paper',
      py: 4,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
    }}
  >
    <Container maxWidth="md">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <Typography
          variant="h4"
          align="center"
          color="text.primary"
          gutterBottom
          sx={{ fontFamily: "Special Gothic Expanded One, Lato, sans-serif" }}
        >
          Prediction Results
        </Typography>
        
        <Typography
          variant="h6"
          align="center"
          color="text.secondary"
          gutterBottom
          sx={{ mb: 4 }}
        >
          {predictions.player_name} vs {predictions.opponent_team_abv}
        </Typography>

        {/* Predictions Grid */}
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: 2,
            mb: 4
          }}
        >
          {Object.entries(predictions.predictions).map(([stat, value]) => (
            <Box
              key={stat}
              sx={{
                p: 2,
                bgcolor: 'white',
                borderRadius: 2,
                boxShadow: 1,
                textAlign: 'center'
              }}
            >
              <Typography variant="h6" color="primary.main" gutterBottom>
                {prettifyStatName(stat)}
              </Typography>
              <Typography variant="h4" fontWeight="bold">
                {typeof value === 'number' ? value.toFixed(1) : value}
              </Typography>
            </Box>
          ))}
        </Box>

        {/* Prop Line Comparisons */}
        <Typography
          variant="h5"
          align="center"
          color="text.primary"
          gutterBottom
          sx={{ fontFamily: "Special Gothic Expanded One, Lato, sans-serif", mt: 4 }}
        >
          Prop Line Analysis
        </Typography>
        
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {Object.entries(predictions.vs_prop_line).map(([stat, recommendation]) => (
            <Box
              key={stat}
              sx={{
                p: 2,
                bgcolor: recommendation.includes('OVER') ? '#e8f5e8' : '#fff3e0',
                borderRadius: 1,
                border: recommendation.includes('OVER') ? '1px solid #4caf50' : '1px solid #ff9800',
                display: 'flex',
                alignItems: 'center',
                width: '100%',
              }}
            >
              <Typography variant="body1">
                <strong>{prettifyStatName(stat)}:</strong> {recommendation}
              </Typography>
            </Box>
          ))}
        </Box>
      </motion.div>
    </Container>
  </Box>
)}


        {/* Footer */}
      <Box sx={{ bgcolor: 'background.paper', p: 6 }} component="footer">
        <Typography variant="h6" align="center" gutterBottom>
          HoopProphet
        </Typography>
        <Typography
          variant="subtitle1"
          align="center"
          color="text.secondary"
          component="p"
        >
          Powered by <a href="https://github.com/swar/nba_api/tree/master/docs/nba_api/stats/endpoints">NBA API</a>
        </Typography>
      </Box>
    </ThemeProvider>
  );
}

export default App;
