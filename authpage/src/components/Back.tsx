import React from "react";
import config from "../config";
import "./Back.scss";

const Back = () => {

    const handleClick = () => {
        window.location.replace(config.client_location)
    }

    return (
        <div className="back" onClick={handleClick}>
            <svg id="" xmlns="http://www.w3.org/2000/svg" className="backArrow" viewBox="0 0 24 24"><path d="M13.025 1l-2.847 2.828 6.176 6.176h-16.354v3.992h16.354l-6.176 6.176 2.847 2.828 10.975-11z" /></svg>
            <p>Terug</p>
        </div>
    )
}

export default Back;




