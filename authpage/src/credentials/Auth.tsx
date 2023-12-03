import React, {useEffect, useState} from "react";
import {clientLogin} from "../functions/authenticate";
import config from "../config";
import "../index.scss";
import "./Auth.scss"
import {back_post, catch_api} from "../functions/api";
import {new_err} from "../functions/error";
import Back from "../components/Back";
import Title from "../components/Title";

const login_url = `${config.client_location}/lg`


const Auth = () => {
    const [username, setUsername] = useState("")
    const [password, setPassword] = useState("")
    // \u00A0 = &nbsp;
    const [status, setStatus] = useState("\u00A0")
    const [info, setInfo] = useState("\u00A0")
    const [showLink, setShowLink] = useState(false)
    const [showForgot, setShowForgot] = useState(false)
    const [forgotEmail, setForgotEmail] = useState("")
    const [forgotOk, setForgotOk] = useState(false)
    const [forgotStatus, setForgotStatus] = useState("\u00A0")
    const [definedUser, setDefinedUser] = useState(false)
    const [redirect, setRedirect] = useState(`${config.auth_location}/oauth/callback`)
    const [load, setLoad] = useState(false)

    const handleSubmit = async (evt: React.FormEvent<HTMLFormElement>) => {
        evt.preventDefault()

        // login
        let flow_id = (new URLSearchParams(window.location.search)).get("flow_id");
        if (flow_id == null) {

            console.log(new_err("bad_auth", "Flow ID not set!", "auth_flow_missing").j())
            setStatus("Er is iets mis met de link, probeer het nogmaals via deze ")
            setShowLink(true)
            return
        }
        const code = await clientLogin(username, password, flow_id)

        if (code === undefined || code == null) {
            console.log("No code received!")
            setStatus("Er is iets misgegaan! Controleer je e-mail en wachtwoord en probeer het opnieuw.")
            setShowLink(false)
            return
        }


        // Is set to zero if not valid on load, see below
        if (redirect === "0") {
            setStatus("Er is iets mis met de link, probeer het nogmaals via deze ")
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
        let extra = (new URLSearchParams(window.location.search)).get("extra");
        if (definedUser !== null) {
            setUsername(definedUser)
            setDefinedUser(true)
        }

        // So 'client:email/update/' is an example of a redirect that will lead to the /email/update/ of the frontend
        if (redirect !== null) {
            setRedirect("0")
            const splitRedirect = redirect.split(':')
            const side = splitRedirect[0]
            const endpoint = splitRedirect[1]

            if (redirect in config.allowed_redirects) {
                const writeInfo = config.allowed_redirects[redirect]
                setInfo(writeInfo(extra == null ? "" : extra))
                if (side === "client") {
                    setRedirect(`${config.client_location}/${endpoint}`)
                } else if (side === "server") {
                    //setRedirect(`${config.auth_location}/${endpoint}`)
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
        <div className="backend_page">
            <Back />
            <Title title="Inloggen" />
            <div className="form_container">
                {info &&
                    <p className="largeText">{info}</p>
                }   
                {showForgot
                    ?   <form className="form" onSubmit={handleSubmitForgot}>
                            <label className="forgotLabel" htmlFor="forgotEmail">Vul je e-mail hieronder in om een mail te ontvangen waarmee je je wachtwoord opnieuw in kunt stellen.</label>
                            <input id="forgotEmail" placeholder="E-mail" type="text" value={forgotEmail}
                                onChange={e => setForgotEmail(e.target.value)}/>
                            <p className={"formStatus " + (forgotOk ? "okForgot" : "badForgot")}>{forgotStatus} </p>
                            <button id="forgot_submit_button" type="submit">Verzenden</button>
                            <button type="button" onClick={handleForgot} className="forgotPassword">Inloggen?</button>
                            
                        </form> 
                    :   <form className="form" onSubmit={handleSubmit}>
                            <input disabled={definedUser} id="username" placeholder="E-mail" type="text" value={username}
                                onChange={e => setUsername(e.target.value)}/>
                            <input type="password" placeholder="Wachtwoord" value={password}
                            onChange={e => setPassword(e.target.value)} />
                            <p className="formStatus">{status}{showLink && <a href={login_url}>link</a>}</p>
                            <button id="submit_button" type="submit">Inloggen</button>                     
                            <button type="button" onClick={handleForgot} className="forgotPassword">Wachtwoord vergeten?</button>
                        </form>
                }
            </div>
            
        </div>
    )
}

export default Auth;




