import React from "react";
import config from "../config";

const Back = () => {

    const handleClick = () => {
        window.location.replace(config.client_location)
    }

    return (
        <div className="backButton" onClick={handleClick}>
            <svg width="100%" height="100%" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg" fill = "#FFFFFF"><path d="M19 7v6c0 1.103-.896 2-2 2H3v-3h13V8H5v2L1 6.5 5 3v2h12a2 2 0 0 1 2 2z"/></svg>
        </div>
    )
}

export default Back;




