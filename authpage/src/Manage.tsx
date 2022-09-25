import React, {ChangeEvent, FormEvent, Suspense, useEffect, useState} from "react";
import "./Register.scss";
import {passUpdate} from "./Authenticate";
import config from "./config";
const PasswordStrength = React.lazy(() => import('./PasswordStrength'));

const redirectUrl = `${config.client_location}/registered`

const Manage = () => {
    const [submitted, setSubmitted] = useState("")
    const [passScore, setPassScore] = useState(0)
    const [preStatus, setPreStatus] = useState("")
    const [status, setStatus] = useState("\u00A0")
    const [handled, setHandled] = useState(false)
    const [urlOk, setUrlOk] = useState(false)
    const [password, setPassword] = useState("")
    const [passwordConfirm, setPasswordConfirm] = useState("")
    const [flowId, setFlowId] = useState("")
    const [email, setEmail] = useState("")

    const somethingWrong = () => {
        setStatus("Er is iets misgegaan!")
    }

    const formIsValid = () => {
        if (passScore < 2) {
            setStatus("Je wachtwoord is te zwak, maak het langer of onregelmatiger")
            return false;
        }
        else if (password != passwordConfirm) {
            setStatus("De wachtwoorden zijn niet gelijk")
            return false;
        }
        setStatus("")
        return true;
    }

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault()

        if (formIsValid()) {
            passUpdate(email, flowId, password).then(
                (result) => {
                    if (result) {
                        window.location.assign(redirectUrl)
                    } else {
                        somethingWrong()
                    }
                },
                () => somethingWrong()
            )
        }
    }

    const handleSubmitClick = () => {
        setSubmitted("submitted")
    }

    const badConfirm = () => {
        setPreStatus("The reset link is incorrect or has expired. Please try again.")
    }

    const handleLoad = async () => {
        const source_params = (new URLSearchParams(window.location.search))
        const flow_id = source_params.get("reset_id")
        const email = source_params.get("email")
        if (flow_id === null || email === null) {
            badConfirm()
        } else {
            setUrlOk(true)
            setFlowId(flow_id)
            setEmail(email)
        }

        setHandled(true)
    }

    useEffect(() => {
        if (!handled) {
            handleLoad().catch();
        }
    }, [handled]);

    return (
        <div>
            <h1 className="title">Change password</h1>
            {urlOk && (
                <><p className="largeText">Hallo! You can reset your password for {email} below.</p>
                <form className="authForm" onSubmit={handleSubmit}>
                    <div className="formContents">
                        <input required className={submitted}  id="password" type="password" placeholder="Nieuw wachtwoord" name="password" value={password}
                               onChange={e => setPassword(e.target.value)}/>
                        {/** The Suspense is used because the library used for loading is quite big, so it is loaded in the background after page load **/}
                        <Suspense fallback={<div className="passBar1">""</div>}><PasswordStrength password={password} passScore={passScore} setPass={setPassScore}/></Suspense>
                        <input className={submitted} required id="passwordConfirm" type="password" placeholder="Herhaal wachtwoord" name="passwordConfirm" value={passwordConfirm}
                               onChange={e => setPasswordConfirm(e.target.value)}/>
                    </div>
                    <button className="authButton" id="submit_button" onClick={handleSubmitClick} type="submit">Opnieuw instellen</button><br />
                    <p className="formStatus">{status}</p>
                </form></>
            )}
            {!urlOk && (
                <p className="largeText">{preStatus}</p>
            )}
        </div>
    )
}

export default Manage;




