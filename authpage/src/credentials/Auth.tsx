import React, {useEffect, useState} from "react";
import {clientLogin} from "../functions/authenticate";
import config from "../config";
import "./Auth.scss"
import {back_post, catch_api} from "../functions/api";
import {new_err} from "../functions/error";

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
    const [definedUser, setDefinedUser] = useState(false)
    const [redirect, setRedirect] = useState(`${config.auth_location}/oauth/callback`)
    const [load, setLoad] = useState(false)

    const handleSubmit = async (evt: React.FormEvent<HTMLFormElement>) => {
        evt.preventDefault()

        // login
        let flow_id = (new URLSearchParams(window.location.search)).get("flow_id");
        if (flow_id == null) {

            console.log(new_err("bad_auth", "Flow ID not set!", "auth_flow_missing").j())
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


        // Is set to zero if not valid on load, see below
        if (redirect === "0") {
            setStatus("Er is iets mis met de link, probeer het nogmaals via deze: ")
            setShowLink(true)
            return
        } else {
            const params = new URLSearchParams({
                flow_id,
                code
            })
            const redirectUrl = `${redirect}?` + params.toString()
            window.location.assign(redirectUrl)
        }
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

    const handleLoad = () => {
        let definedUser = (new URLSearchParams(window.location.search)).get("user");
        let redirect = (new URLSearchParams(window.location.search)).get("redirect");
        if (definedUser !== null) {
            setUsername(definedUser)
            setDefinedUser(true)

        }

        // So 'client:email/update/' is an example of a redirect that will lead to the /email/update/ of the frontend
        if (redirect !== null) {
            console.log(redirect)
            setRedirect("0")
            const splitRedirect = redirect.split(':')
            if (config.allowed_redirects.includes(splitRedirect[1])) {
                if (splitRedirect[0] === "client") {
                    setRedirect(`${config.client_location}/${splitRedirect[1]}`)
                } else if (splitRedirect[0] === "server") {
                    setRedirect(`${config.auth_location}/${splitRedirect[1]}`)
                }
            }
        }
    }

    useEffect(() => {
        if (!load) {
            handleLoad()
            setLoad(true)
        }
    }, [])

    return (
        <>
            <h1 className="title">Login</h1>
            <form className="authForm" onSubmit={handleSubmit}>
                <div className="formContents">
                    <input disabled={definedUser} id="username" placeholder="Email" type="text" value={username}
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




