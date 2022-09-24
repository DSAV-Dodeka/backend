import React, {ChangeEvent, FormEvent, Suspense, useEffect, useReducer, useState} from "react";
import {base64ToBin} from "./encode";
import {clientLogin, clientRegister} from "./Authenticate";
import {RegisterState} from "./Register";
import PasswordStrength from "./PasswordStrength";

const Manage = () => {
    const [submitted, setSubmitted] = useState("")
    const [passScore, setPassScore] = useState(0)
    const [status, setStatus] = useState("")

    const [password, setPassword] = useState("")
    const [passwordConfirm, setPasswordConfirm] = useState("")

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
            clientLogin(password).then(
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

    const handleFormChange = (event: ChangeEvent<HTMLInputElement>) => {
        const { name, value } = event.target
        if (name === "password") {
            setPassword(value)
        } else if (name === "passwordConfirm") {
            setPasswordConfirm(value)
        }
    }

    return (
        <div>
            <h1 className="title">Change password</h1>
            <form className="registerForm" onSubmit={handleSubmit}>
                <div className="formContents">
                    <input required className={submitted}  id="password" type="password" placeholder="Nieuw wachtwoord" name="password" value={password}
                           onChange={handleFormChange}/>
                    {/** The Suspense is used because the library used for loading is quite big, so it is loaded in the background after page load **/}
                    <Suspense fallback={<div className="passBar1">""</div>}><PasswordStrength password={password} passScore={passScore} setPass={setPassScore}/></Suspense>
                    <input className={submitted} required id="passwordConfirm" type="password" placeholder="Herhaal wachtwoord" name="passwordConfirm" value={passwordConfirm}
                           onChange={handleFormChange}/>
                </div>
                <button className="registerButton" id="submit_button" onClick={handleSubmitClick} type="submit">Registreer</button><br />
                <p className="schrijfInStatus">{status}</p>
            </form>
        </div>
    )
}

export default Manage;




