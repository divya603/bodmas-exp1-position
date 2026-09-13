// Comprehension quiz shown after the instructions (design.js). All questions
// must be answered correctly; otherwise the participant returns to the
// instructions. Questions 3 and 4 check the two reasons to disagree that
// practice items P2 and P3 teach: a different mistake, and no chance to show
// the stated belief.
export const QUIZ_QUESTIONS = [
  {
    id: 'pg1',
    questions: [
      {
        id: 'q1',
        question: 'What should your rating be based on?',
        multiSelect: false,
        answers: [
          "How well the statement explains the student's work",
          'Whether the final answer is correct',
          'How many steps the student used',
          'How long the problem is',
        ],
        correctAnswer: ["How well the statement explains the student's work"],
      },
      {
        id: 'q2',
        question: 'How many mistakes does each student make?',
        multiSelect: false,
        answers: ['Exactly one', 'None', 'Two', 'It varies'],
        correctAnswer: ['Exactly one'],
      },
      {
        id: 'q3',
        question:
          "A student's mistake is doing subtraction before multiplication. The statement says the student believes " +
          'addition should be done before multiplication. Should you agree or disagree?',
        multiSelect: false,
        answers: ['Agree', 'Disagree'],
        correctAnswer: ['Disagree'],
      },
      {
        id: 'q4',
        question:
          'A problem has no brackets. The statement says the student believes you should calculate outside the ' +
          "brackets before what's inside them. Should you agree or disagree?",
        multiSelect: false,
        answers: ['Agree', 'Disagree'],
        correctAnswer: ['Disagree'],
      },
    ],
  },
]
