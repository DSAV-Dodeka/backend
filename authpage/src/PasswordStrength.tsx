import React, {useEffect} from "react";
import { zxcvbn, zxcvbnOptions } from '@zxcvbn-ts/core'
import zxcvbnCommonPackage from '@zxcvbn-ts/language-common'

export interface Props {
    password: string;
    passScore: number
    setPass: React.Dispatch<React.SetStateAction<number>>
}

zxcvbnOptions.setOptions({
    dictionary: zxcvbnCommonPackage.dictionary,
    graphs: zxcvbnCommonPackage.adjacencyGraphs,
})

const mapper = (score: number): string => {
    return ['weak', 'weak', 'okay', 'good', 'strong'].at(score) || 'weak'
}

const PasswordStrength: React.FC<Props> = (props) => {
    useEffect(() => {
        const score = zxcvbn(props.password).score
        props.setPass(score)
    });

    return (
        <div className={"passBar" + (props.passScore + 1)}>Your password is <strong>{mapper(props.passScore)}</strong></div>
    )
}

export { PasswordStrength as default }
