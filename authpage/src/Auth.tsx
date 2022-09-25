import React, {useEffect, useState} from "react";
import {clientLogin} from "./Authenticate";
import config from "./config";
import "./Auth.scss"
import {back_post, catch_api} from "./api";

const login_url = `${config.client_location}/lg`

const Auth = () => {
    const [username, setUsername] = useState("")
    const [password, setPassword] = useState("")
    // \u00A0 = &nbsp;
    const [status, setStatus] = useState("\u00A0")
    const [showLink, setShowLink] = useState(false)
    const [showForgot, setShowForgot] = useState(false)
    const [forgotEmail, setForgotEmail] = useState("")
    const [forgotOk, setForgotOk] = useState(false)
    const [forgotStatus, setForgotStatus] = useState("")

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
            setStatus("Er is iets misgegaan! Is je wachtwoord correct?")
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

    const handleSubmitForgot = async (evt: React.FormEvent<HTMLFormElement>) => {
        evt.preventDefault()

        const req = {
            "email": forgotEmail
        }
        try {
            await back_post("update/password/reset/", req)
            setForgotStatus("Email sent!")
            setForgotOk(true)
        } catch (e) {
            setForgotStatus("Er is iets misgegaan!")
            setForgotOk(false)
            const err = await catch_api(e)
            console.log(JSON.stringify(err))
        }
    }

    const handleForgot = () => {
        setShowForgot((s) => !s)
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
                    <form className="forgotForm" onSubmit={handleSubmitForgot}>
                        <div className="formContents ">
                            <label htmlFor="forgotEmail">Vul je email hieronder in om je wachtwoord opnieuw in te stellen.</label>
                            <input id="forgotEmail" placeholder="Email" type="text" value={forgotEmail}
                                   onChange={e => setForgotEmail(e.target.value)}/>
                            <button id="forgot_submit_button" type="submit">Verzenden</button>
                            <p className={"formStatus " + (forgotOk ? "okForgot" : "badForgot")}>{forgotStatus}</p>
                        </div>
                    </form>
                </div>
            )}
        </>
    )
}

export default Auth;




