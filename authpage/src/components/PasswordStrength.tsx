import React, {useEffect} from "react";
import { zxcvbn, zxcvbnOptions } from '@zxcvbn-ts/core'
import { dictionary, adjacencyGraphs } from '@zxcvbn-ts/language-common'

export interface Props {
    password: string;
    passScore: number
    setPass: React.Dispatch<React.SetStateAction<number>>
}

zxcvbnOptions.setOptions({
    dictionary,
    graphs: adjacencyGraphs,
})

const mapper = (score: number): string => {
    return ['zwak', 'zwak', 'oké', 'goed', 'sterk'].at(score) || 'zwak'
}

const PasswordStrength: React.FC<Props> = (props) => {
    useEffect(() => {
        const score = zxcvbn(props.password).score
        props.setPass(score)
    });

    return (
        <div className={"passBar" + (props.passScore + 1)}>Je wachtwoord is <strong>{mapper(props.passScore)}</strong></div>
    )
}

export { PasswordStrength as default }
