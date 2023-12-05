import React, {
    useReducer,
    Suspense,
    FormEvent,
    ChangeEvent,
    FocusEvent,
    useState,
    useEffect,
    MouseEvent
} from "react";
import "./Register.scss";
import "../../index.scss";
import config from "../../config";
import {clientLogin, clientRegister} from "../../functions/authenticate";
import {base64ToBin} from "../../functions/encode";
import Back from "../../components/Back";
import {z} from "zod";
import {new_err} from "../../functions/error";
import Logo from "../../logo.svg?react"
import Title from "../../components/Title";
// Imported lazily due to large library size
const PasswordStrength = React.lazy(() => import('../../components/PasswordStrength'));

const registerReducer = (state: RegisterState, action: RegisterAction): RegisterState => {
    switch (action.type) {
        case 'reload':
            return action.new_state
        case 'change': // Both 'change' and 'change_bool' have same effect
        case 'change_bool':
            return {
                ...state,
                [action.field]: action.value
            }
        default:
            throw new Error()
    }

}

export type RegisterState = {
    firstname: string,
    lastname: string,
    email: string,
    phone: string,
    callname: string,
    password: string,
    password_confirm: string,
    date_of_birth: string,
    birthday_check: boolean,
    student: boolean,
    eduinstitution: string,
    eduinstitution_other: string,
    register_id: string
}

type RegisterAction =
    | { type: 'reload', new_state: RegisterState}
    | { type: 'change', field: string, value: string }
    | { type: 'change_bool', field: string, value: boolean }

let initialState: RegisterState = {
    register_id: "",
    firstname: "",
    lastname: "",
    email: "",
    phone: "",
    callname: "",
    password: "",
    password_confirm: "",
    date_of_birth: "2019-02-25",
    birthday_check: false,
    student: false,
    eduinstitution: "TU Delft",
    eduinstitution_other: ""
}

let focus:boolean = false;

const handleFocus = (event: FocusEvent<HTMLInputElement>) => {
    if (!focus) {
        event.target.blur();
        event.target.type = 'date';
        focus = true;
        clearTimeout(0);
        event.target.focus();
    }
}

const handleBlur = (event: FocusEvent<HTMLInputElement>) => {
    if (focus) {
        event.target.type = 'text';
        focus = false;
    }
}

const RegisterInfo = z.object({
    register_id: z.string(),
    firstname: z.string(),
    lastname: z.string(),
    email: z.string(),
    phone: z.string(),
})

const redirectUrl = `${config.client_location}/registered`

const Register = () => {
    const readUrlSearch = (): RegisterState => {
        const source_params = (new URLSearchParams(window.location.search))
        const info_param = source_params.get("info")
        if (info_param === null) {
            throw new Error("No info given!")
        }
        const info_bytes = base64ToBin(info_param)
        const decoder = new TextDecoder()
        const info_str = decoder.decode(info_bytes)
        const info = JSON.parse(info_str)
        const reg_info = RegisterInfo.parse(info)
        return {
            ...initialState,
            ...reg_info
        }
    }

    const [handled, setHandled] = useState(false)
    const [infoOk, setInfoOk] = useState(false)
    const [state, dispatch] = useReducer(
        registerReducer,
        initialState,
    )
    const [submitted, setSubmitted] = useState("")
    const [passScore, setPassScore] = useState(0)
    const [status, setStatus] = useState("\u00A0")


    useEffect(() => {
        if (!handled) {
            try {
                const reducerInitial = readUrlSearch()
                setInfoOk(true)
                dispatch({type: 'reload', new_state: reducerInitial})
            } catch (e) {
                setInfoOk(false)
            }
            setHandled(true)
        }
    }, [handled]);

    const somethingWrong = () => {
        setStatus("Er is iets misgegaan!")
    }

    const formIsValid = () => {
        if (passScore < 2) {
            setStatus("Je wachtwoord is te zwak, maak het langer of onregelmatiger.")
            return false;
        }
        else if (state.password != state.password_confirm) {
            setStatus("De wachtwoorden zijn niet gelijk.")
            return false;
        }
        setStatus("")
        return true;
    }

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault()

        if (formIsValid()) {
            var eduinstitution;
            if (!state.student) {
                eduinstitution = "";
            } else {
                eduinstitution = state.eduinstitution === "Anders, namelijk:" 
                    ? state.eduinstitution_other 
                    : state.eduinstitution;
            }
            const submitState = { ...state, eduinstitution }

            clientRegister(submitState).then(
                (result) => {
                    if (result) {
                        window.location.assign(redirectUrl)
                    } else {
                        console.log(new_err("bad_register", "Bad register result!", "register_false").j())
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
        <div className="backend_page">
            <Back />
            <Title title="Registeren" />
            {!infoOk && handled &&
            <p className="largeText">Deze link voor het registratieformulier werkt niet, probeer het opnieuw of vraag het bestuur om een nieuwe link!</p>
            }
            {infoOk &&
            <form className="form" onSubmit={handleSubmit}>
                <input disabled className={submitted} required id="name" type="text" placeholder="Voornaam" name="name" value={state.firstname}
                       onChange={handleFormChange}/>
                <input disabled className={submitted} required id="surname" type="text" placeholder="Achternaam" name="surname" value={state.lastname}
                       onChange={handleFormChange}/>
                <input disabled className={submitted} required id="email" type="text" placeholder="E-mail" name="email" value={state.email}
                       onChange={handleFormChange}/>
                <input disabled className={submitted} required id="phone" type="text" placeholder="Telefoonnummer" name="phone" value={state.phone}
                       onChange={handleFormChange}/>
                <p className="maybeMistakeText">Staat hierboven een foutje? Het kan ook na registratie aangepast worden, laat het aan ons weten!</p>
                <input required className={"formPassword " + submitted}  id="password" type="password" placeholder="Wachtwoord" name="password" value={state.password}
                       onChange={handleFormChange}/>
                {/** The Suspense is used because the library used for loading is quite big, so it is loaded in the background after page load **/}
                <Suspense fallback={<div className="passBar1">""</div>}><PasswordStrength password={state.password} passScore={passScore} setPass={setPassScore}/></Suspense>
                <input className={submitted} required id="password_confirm" type="password" placeholder="Herhaal wachtwoord" name="password_confirm" value={state.password_confirm}
                       onChange={handleFormChange}/>
                <div className="dropdown">
                <label>Geboortedatum:</label>
                <input className={submitted} required id="date_of_birth" type="date" placeholder="Geboortedatum" name="date_of_birth" value={state.date_of_birth}
                        onChange={handleFormChange} />
                </div>
                
                <div className="checkbox">
                    <label >Leden mogen mijn verjaardag en leeftijd zien</label>
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
                    <select id="eduinstitution" name="eduinstitution" value={state.eduinstitution}
                            onChange={handleSelectChange}>
                        <option>TU Delft</option>
                        <option>Haagse Hogeschool - Delft</option>
                        <option>Haagse Hogeschool - Den Haag</option>
                        <option>Hogeschool Inholland - Delft</option>
                        <option>Anders, namelijk:</option>
                    </select>
                </div>
                <input className={"" + (state.student && state.eduinstitution === "Anders, namelijk:" ? "" : " inputHidden")} id="eduinstitution_other" type="text" placeholder="Onderwijsinstelling" name="eduinstitution_other" value={state.eduinstitution_other}
                        onChange={handleFormChange} />

                <br />
                <button className="authButton" id="submit_button" onClick={handleSubmitClick} type="submit">Registreer</button><br />
                <p className="buttonText">Door op registeer te klikken ga je akkoord met het eerder genoemde <a href="https://dsavdodeka.nl/files/privacyverklaring_dodeka_jan23.pdf" target="_blank" rel="noreferrer" className="privacy_link">privacybeleid</a></p>
                <p className="formStatus">{status}</p>
            </form>}
        </div>
    )
}

export default Register;