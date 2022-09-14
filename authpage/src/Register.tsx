import React, {useReducer, Suspense, FormEvent, ChangeEvent, FocusEvent, useState} from "react";
import "./Register.scss";
import config from "./config";
import {clientRegister} from "./Authenticate";
// Imported lazily due to large library size
const PasswordStrength = React.lazy(() => import('./PasswordStrength'));

const registerReducer = (state: RegisterState, action: RegisterAction): RegisterState => {
    switch (action.type) {
        case 'change': // Both 'change' and 'change_bool' have same effect
        case 'change_bool':
            return {
                ...state,
                [action.field]: action.value
            }
        case 'register':
            clientRegister(state).then(r => {

            })
            return state
        default:
            throw new Error()
    }

}

export type RegisterState = {
    name: string,
    surname: string,
    email: string,
    phone: string,
    callname: string,
    password: string,
    password_confirm: string,
    date_of_birth: string,
    birthday_check: boolean,
    student: boolean,
    onderwijsinstelling: string,
    onderwijsinstelling_overig: string,
    register_id: string
}

type RegisterAction =
    | { type: 'register' }
    | { type: 'reset'}
    | { type: 'change', field: string, value: string }
    | { type: 'change_bool', field: string, value: boolean }

let initialState: RegisterState = {
    name: "",
    surname: "",
    email: "",
    phone: "",
    callname: "",
    password: "",
    password_confirm: "",
    date_of_birth: "",
    birthday_check: false,
    student: false,
    onderwijsinstelling: "",
    onderwijsinstelling_overig: "",
    register_id: ""
}

const handleFocus = (event: FocusEvent<HTMLInputElement>) => {
    event.target.type = 'date';
}

const handleBlur = (event: FocusEvent<HTMLInputElement>) => {
    event.target.type = 'text';
}

const Register = () => {
    const readUrlS = (): RegisterState => {
        const source_params = (new URLSearchParams(window.location.search))
        const register_id = source_params.get("register_id") || "error"
        const email = source_params.get("email") || "error"
        const name = source_params.get("name") || "error"
        const surname = source_params.get("surname") || "error"
        const phone = source_params.get("phone") || "error"
        return {
            ...initialState,
            register_id,
            email,
            name,
            surname,
            phone
        }
    }

    const [state, dispatch] = useReducer(
        registerReducer,
        readUrlS(),
    )
    const [submitted, setSubmitted] = useState("")
    const [passScore, setPassScore] = useState(0)
    const [status, setStatus] = useState("")

    const formIsValid = () => {
        if (passScore < 2) {
            setStatus("Je wachtwoord is te zwak, maak het langer of onregelmatiger")
            return false;
        }
        else if (state.password != state.password_confirm) {
            setStatus("De wachtwoorden zijn niet gelijk")
            return false;
        }
        setStatus("")
        return true;
    }

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault()
        const source_params = (new URLSearchParams(window.location.search))
        let registerId = source_params.get("register_id");
        registerId = registerId != null ? registerId : ""
        dispatch({type: 'change', field: "register_id", value: registerId})
        if (formIsValid()) {
            dispatch({type: 'register'})
        }
    }

    const handleSubmitClick = () => {
        setSubmitted("submitted")
        console.log("hi")
    }

    const handleFormChange = (event: ChangeEvent<HTMLInputElement>) => {
        const { name, value } = event.target
        dispatch({type: 'change', field: name, value})
    }

    const handleSelectChange = (event: ChangeEvent<HTMLSelectElement>) => {
        const { name, value } = event.target
        dispatch({type: 'change', field: name, value})
    }

    const handleCheckboxChange = (event: ChangeEvent<HTMLInputElement>) => {
        const { name, checked } = event.target
        dispatch({type: 'change_bool', field: name, value: checked});
    }

    return (
        <div>
            <h1 className="title">Register</h1>
            <form className="registerForm" onSubmit={handleSubmit}>
                <div className="formContents">
                    <input disabled className={submitted} required id="name" type="text" placeholder="Voornaam" name="name" value={state.name}
                           onChange={handleFormChange}/>
                    <input disabled className={submitted} required id="surname" type="text" placeholder="Achternaam" name="surname" value={state.surname}
                           onChange={handleFormChange}/>
                    <input disabled className={submitted} required id="email" type="text" placeholder="E-mail" name="email" value={state.email}
                           onChange={handleFormChange}/>
                    <input disabled className={submitted} required id="phone" type="text" placeholder="Telefoonnummer" name="phone" value={state.phone}
                           onChange={handleFormChange}/>
                    <p>Staat hierboven een foutje? Laat het weten aan het bestuur en ze zullen je een nieuwe e-mail sturen!</p>
                    <input className={submitted} required id="name" type="text" placeholder="Roepnaam" name="callname" value={state.callname}
                           onChange={handleFormChange}/>
                    <input required className={"password " + submitted}  id="password" type="password" placeholder="Wachtwoord" name="password" value={state.password}
                           onChange={handleFormChange}/>
                    {/** The Suspense is used because the library used for loading is quite big, so it is loaded in the background after page load **/}
                    <Suspense fallback={<div className="passBar1">""</div>}><PasswordStrength password={state.password} passScore={passScore} setPass={setPassScore}/></Suspense>
                    <input className={submitted} required id="password_confirm" type="password" placeholder="Herhaal wachtwoord" name="password_confirm" value={state.password_confirm}
                           onChange={handleFormChange}/>
                    <input className={submitted} required id="date_of_birth" type="text" placeholder="Geboortedatum" onFocus={handleFocus} onBlur={handleBlur} name="date_of_birth" value={state.date_of_birth}
                            onChange={handleFormChange} />
                    <div className="checkbox">
                        <label >Leden mogen mijn verjaardag zien</label>
                        <input className={submitted} id="birthday_check" type="checkbox" name="birthday_check"
                                onChange={handleCheckboxChange}/>
                    </div>
                    <div className="checkbox">
                        <label >Ik ben student</label>
                        <input id="student" type="checkbox" name="student"
                                onChange={handleCheckboxChange}/>
                    </div>
                    <div className={"dropdown" + (state.student ? "": " inputHidden")}>
                        <label >Onderwijsinstelling:</label>
                        <select id="onderwijsinstelling" name="onderwijsinstelling" value={state.onderwijsinstelling}
                                onChange={handleSelectChange}>
                            <option value="TU Delft">TU Delft</option>
                            <option value="Haagse Hogeschool - Delft">Haagse Hogeschool - Delft</option>
                            <option>Haagse Hogeschool - Den Haag</option>
                            <option>Hogeschool Inholland - Delft</option>
                            <option value="Anders, namelijk:">Anders, namelijk:</option>
                        </select>
                    </div>
                    <input className={"" + (state.onderwijsinstelling === "Anders, namelijk:" ? "" : " inputHidden")} id="onderwijsinstelling_overig" type="text" placeholder="Onderwijsinstelling" name="onderwijsinstelling_overig" value={state.onderwijsinstelling_overig}
                            onChange={handleFormChange} />
                    <div className="checkbox">
                        <label >Ik accepteer het privacybeleid</label>
                        <input className={submitted} required id="privacy" type="checkbox" name="privacy"
                                onChange={handleCheckboxChange}/>
                    </div>
                    <p className="schrijfInStatus">{status}</p>
                    
                </div>
                <button className="registerButton" id="submit_button" onClick={handleSubmitClick} type="submit">Registreer</button><br />
            </form>
        </div>
    )
}

export default Register;