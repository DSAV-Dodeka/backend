import React, {FormEvent, Suspense, useEffect, useState} from "react";
import "../../index.scss";
import "../register/Register.scss";
import {passUpdate} from "../../functions/authenticate";
import config from "../../config";
import {new_err} from "../../functions/error";
import Back from "../../components/Back";
import Title from "../../components/Title";
const PasswordStrength = React.lazy(() => import('../../components/PasswordStrength'));

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
            setStatus("Je wachtwoord is te zwak, maak het langer of onregelmatiger.")
            return false;
        }
        else if (password != passwordConfirm) {
            setStatus("De wachtwoorden zijn niet gelijk.")
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
                        console.log(new_err("bad_pass_update", "Bad pass update result!", "pass_update_false").j())
                        somethingWrong()
                    }
                },
                (e) => {
                    console.log(e)
                    somethingWrong()
                }
            )
        }
    }

    const handleSubmitClick = () => {
        setSubmitted("submitted")
    }

    const badConfirm = () => {
        setPreStatus("De herstellink is incorrect of verlopen. Probeer het opnieuw!")
    }

    const handleLoad = () => {
        const source_params = (new URLSearchParams(window.location.search))
        const flow_id = source_params.get("reset_id")
        const email = source_params.get("email")
        if (flow_id === null || email === null) {
            console.log(new_err("bad_manage_load", "Flow ID or email not set!", "manage_load_missing").j())
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
            handleLoad();
        }
    }, [handled]);

    return (
        <div className="backend_page">
            <Back />
            <Title title="Wachtwoord veranderen" />
            {urlOk && (
                <><p className="largeText">Wijzig hieronder je wachtwoord voor je account met e-mail: {email}.</p>
                <form className="form" onSubmit={handleSubmit}>
                    <input required className={"formPassword " + submitted}  id="password" type="password" placeholder="Nieuw wachtwoord" name="password" value={password}
                        onChange={e => setPassword(e.target.value)}/>
                    {/** The Suspense is used because the library used for loading is quite big, so it is loaded in the background after page load **/}
                    <Suspense fallback={<div className="passBar1">""</div>}><PasswordStrength password={password} passScore={passScore} setPass={setPassScore}/></Suspense>
                    <input className={submitted} required id="passwordConfirm" type="password" placeholder="Herhaal wachtwoord" name="passwordConfirm" value={passwordConfirm}
                    onChange={e => setPasswordConfirm(e.target.value)}/>
                    <p className="formStatus">{status}</p>
                    <button className="authButton" id="submit_button" onClick={handleSubmitClick} type="submit">Opnieuw instellen</button><br />
                </form></>
            )}
            {!urlOk && (
                <p className="largeText">{preStatus}</p>
            )}
        </div>
    )
}

export default Manage;




