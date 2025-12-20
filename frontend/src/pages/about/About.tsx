import { useNavigate } from "react-router-dom"
import "./home.module.css"
import { ROUTES } from "../../routes";


const About = () => {

  const navigate = useNavigate();

  const playGame = () => {
    navigate(ROUTES.GAME);
  }

  return (
    <div className="about">
      <h1>About Play Tanks</h1>
      <p>
        Play Tanks is an exciting multiplayer tank battle game where players can
        engage in thrilling combat scenarios. Choose your tank, strategize with
        your team, and dominate the battlefield!
      </p>
      <button onClick={playGame}>Play</button>


    </div>
  )
}

export default About