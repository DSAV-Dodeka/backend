import React, {useEffect, useState} from "react";
import {clientLogin} from "./Authenticate";
import config from "./config";
import "./Auth.scss"

const login_url = `${config.client_location}/lg`

const Auth = () => {
    const [username, setUsername] = useState("")
    const [password, setPassword] = useState("")
    const [status, setStatus] = useState("")
    const [showLink, setShowLink] = useState(false)
    const [showForgot, setShowForgot] = useState(false)

    const handleSubmit = async (evt: React.FormEvent<HTMLFormElement>) => {
        evt.preventDefault()


        // login
        let flow_id = (new URLSearchParams(window.location.search)).get("flow_id");
        if (flow_id == null) {
            console.log("No flow_id set!")
            setStatus("Er is iets mis met de link, probeer het nogmaals via deze: ")
            setShowLink(true)
            return
        }
        const code = await clientLogin(username, password, flow_id)

        if (code === undefined || code == null) {
            console.log("No code received!")
            setStatus("Er is iets misgegaan!")
            setShowLink(false)
            return
        }

        const params = new URLSearchParams({
            flow_id,
            code
        })

        const redirectUrl = `${config.auth_location}/oauth/callback?` + params.toString()
        window.location.assign(redirectUrl)
    }

    const handleForgot = () => {

    }

    return (
        <>
            <h1 className="title">Login</h1>
            <form className="authForm" onSubmit={handleSubmit}>
                <div className="formContents">
                    <input id="username" placeholder="Email" type="text" value={username}
                           onChange={e => setUsername(e.target.value)}/>
                    <input type="password" placeholder="Password" value={password}
                           onChange={e => setPassword(e.target.value)} />
                    <button id="submit_button" type="submit">Inloggen</button><br />
                </div>
                <p className="formStatus">{status}{showLink && <a href={login_url}>login</a>}</p>
            </form>
            <br/><button onClick={handleForgot} className="forgotPassword">Wachtwoord vergeten?</button>
            {showForgot && (
                <div>

                </div>
            )}
        </>
    )
}

export default Auth;




